import ast
import builtins
import logging
import math
import multiprocessing
import queue
import sys
import time
import traceback
from collections import abc
from dataclasses import dataclass, field
from datetime import datetime
from io import StringIO
from typing import Any, Optional

_real_import = builtins.__import__

logger = logging.getLogger(__name__)

SAFE_IMPORTS = {
    "pandas",
    "numpy",
    "matplotlib",
    "matplotlib.pyplot",
    "math",
    "statistics",
    "json",
    "re",
    "collections",
    "datetime",
}

BLOCKED_IMPORTS = {
    "os", "sys", "subprocess", "shutil", "socket",
    "pathlib", "glob", "builtins", "importlib",
    "ctypes", "multiprocessing", "threading", "asyncio",
    "pickle", "shelve", "sqlite3",
}

DANGEROUS_BUILTINS = {"open", "exec", "eval", "compile", "input", "__import__"}

_SAFE_BUILTIN_NAMES = {
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "callable", "chr", "classmethod", "complex", "delattr", "dict",
    "dir", "divmod", "enumerate", "filter", "float", "format",
    "frozenset", "getattr", "globals", "hasattr", "hash", "hex", "id",
    "int", "isinstance", "issubclass", "iter", "len", "list", "locals",
    "map", "max", "min", "next", "object", "oct", "ord", "pow", "print",
    "property", "range", "repr", "reversed", "round", "set", "slice",
    "sorted", "staticmethod", "str", "sum", "super", "tuple", "type",
    "vars", "zip",
    "ArithmeticError", "AssertionError", "AttributeError", "BaseException",
    "DeprecationWarning", "EOFError", "Exception", "FloatingPointError",
    "GeneratorExit", "ImportError", "IndentationError", "IndexError",
    "KeyError", "KeyboardInterrupt", "LookupError", "MemoryError",
    "NameError", "NotImplementedError", "OSError", "OverflowError",
    "RecursionError", "ReferenceError", "RuntimeError", "RuntimeWarning",
    "StopIteration", "SyntaxError", "SystemError", "SystemExit",
    "TabError", "TypeError", "UnboundLocalError", "UnicodeDecodeError",
    "UnicodeEncodeError", "UnicodeError", "UnicodeTranslateError",
    "ValueError", "Warning", "ZeroDivisionError",
    "False", "True", "None", "Ellipsis", "NotImplemented",
}


def _build_safe_builtins() -> dict:
    safe = {}
    for name in _SAFE_BUILTIN_NAMES:
        if hasattr(builtins, name):
            safe[name] = getattr(builtins, name)
    return safe


@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    error: Optional[str] = None
    execution_time_seconds: float = 0.0
    result: Any = None


class ImportDenied(Exception):
    pass


class TimeoutError_(Exception):
    pass


class PythonSandbox:
    MAX_OUTPUT_CHARS = 50_000

    def __init__(self, timeout: Optional[int] = None):
        self.default_timeout = timeout or 30

    def execute(self, code: str, timeout: Optional[int] = None, context: Optional[dict] = None) -> SandboxResult:
        timeout = timeout or self.default_timeout

        parent_conn, child_conn = multiprocessing.Pipe(duplex=False)
        process = multiprocessing.Process(
            target=self._run_in_process,
            args=(code, child_conn, context or {}),
        )

        start = time.monotonic()
        process.start()
        process.join(timeout=timeout)
        elapsed = time.monotonic() - start

        if process.is_alive():
            process.terminate()
            process.join()
            return SandboxResult(
                success=False,
                stdout="",
                stderr="",
                error=f"Execution timed out after {timeout} seconds",
                execution_time_seconds=elapsed,
            )

        if parent_conn.poll():
            result = parent_conn.recv()
            result.execution_time_seconds = elapsed
            return result

        return SandboxResult(
            success=False,
            stdout="",
            stderr="",
            error="Process ended without returning a result",
            execution_time_seconds=elapsed,
        )

    def _run_in_process(self, code: str, conn, context: dict):
        try:
            self._validate_ast(code)
        except Exception as e:
            conn.send(SandboxResult(success=False, stdout="", stderr="", error=str(e)))
            return

        context_safe = {k: v for k, v in context.items()
                        if k not in {"__builtins__", "__import__"} and k not in DANGEROUS_BUILTINS}

        safe_builtins = _build_safe_builtins()
        safe_builtins["__import__"] = self._safe_import
        safe_globals = {}
        safe_globals.update(context_safe)
        safe_globals["__builtins__"] = safe_builtins
        for name in DANGEROUS_BUILTINS:
            safe_globals[name] = self._raise_blocked

        stdout_capture = StringIO()
        stderr_capture = StringIO()
        old_stdout = sys.stdout
        old_stderr = sys.stderr

        try:
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture

            exec(code, safe_globals)

            out = stdout_capture.getvalue()[:self.MAX_OUTPUT_CHARS]
            err = stderr_capture.getvalue()[:self.MAX_OUTPUT_CHARS]
            result_value = safe_globals.get("result")
            result_value = self._serialize_result(result_value)
            conn.send(SandboxResult(success=True, stdout=out, stderr=err, result=result_value))
        except Exception:
            out = stdout_capture.getvalue()[:self.MAX_OUTPUT_CHARS]
            err = stderr_capture.getvalue()[:self.MAX_OUTPUT_CHARS]
            tb = traceback.format_exc()
            conn.send(SandboxResult(
                success=False,
                stdout=out,
                stderr=err,
                error=tb,
            ))
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr

    def _validate_ast(self, code: str):
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            raise ValueError(f"Syntax error: {e}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._check_import(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    self._check_import(node.module)
                for alias in node.names:
                    full_name = f"{node.module}.{alias.name}" if node.module else alias.name
                    if full_name not in SAFE_IMPORTS:
                        if alias.name not in ("pyplot",):
                            pass

    def _check_import(self, module_name: str):
        base = module_name.split(".")[0]
        if base in BLOCKED_IMPORTS:
            raise ImportDenied(f"Import '{module_name}' is not allowed for security reasons.")
        if module_name not in SAFE_IMPORTS and base not in ("pandas", "numpy", "matplotlib"):
            if base not in ("math", "statistics", "json", "re", "collections", "datetime"):
                raise ImportDenied(f"Import '{module_name}' is not in the allowed list.")

    @staticmethod
    def _raise_blocked(*args, **kwargs):
        raise RuntimeError("This built-in is disabled for security reasons.")

    @staticmethod
    def _serialize_result(val: Any) -> Any:
        if val is None or isinstance(val, (bool, int, float, str)):
            return val
        if isinstance(val, dict):
            return {k: PythonSandbox._serialize_result(v) for k, v in val.items()}
        if isinstance(val, (list, tuple)):
            return [PythonSandbox._serialize_result(v) for v in val]
        try:
            import numpy as np
            if isinstance(val, np.integer):
                return int(val)
            if isinstance(val, np.floating):
                return float(val)
            if isinstance(val, np.bool_):
                return bool(val)
            if isinstance(val, np.ndarray):
                return PythonSandbox._serialize_result(val.tolist())
        except ImportError:
            pass
        try:
            import pandas as pd
            if isinstance(val, pd.Timestamp):
                return str(val)
            if isinstance(val, pd.Series):
                return PythonSandbox._serialize_result(val.to_dict())
            if isinstance(val, pd.DataFrame):
                return PythonSandbox._serialize_result(val.to_dict(orient="records"))
        except ImportError:
            pass
        return str(val)

    def _safe_import(self, name, *args, **kwargs):
        if name in BLOCKED_IMPORTS:
            raise ImportDenied(f"Import '{name}' is not allowed for security reasons.")
        if name not in SAFE_IMPORTS:
            base = name.split(".")[0]
            if base not in ("pandas", "numpy", "matplotlib", "math", "statistics", "json", "re", "collections", "datetime"):
                raise ImportDenied(f"Import '{name}' is not allowed.")

        try:
            return _real_import(name, *args, **kwargs)
        except Exception as e:
            raise ImportDenied(f"Failed to import '{name}': {e}")
