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
from typing import Optional

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

SAFE_BUILTINS = {
    "abs", "all", "any", "ascii", "bin", "bool", "bytearray", "bytes",
    "callable", "chr", "complex", "dict", "dir", "divmod", "enumerate",
    "filter", "float", "format", "frozenset", "getattr", "hasattr",
    "hash", "hex", "id", "int", "isinstance", "issubclass", "iter",
    "len", "list", "map", "max", "min", "next", "object", "oct",
    "ord", "pow", "print", "property", "range", "repr", "reversed",
    "round", "set", "setattr", "slice", "sorted", "staticmethod",
    "str", "sum", "super", "tuple", "type", "vars", "zip",
    "True", "False", "None",
    "Exception", "ValueError", "TypeError", "KeyError", "IndexError",
    "StopIteration", "RuntimeError", "AttributeError",
    "ImportError", "ModuleNotFoundError", "ZeroDivisionError",
    "ArithmeticError", "LookupError",
    "len", "print", "range", "int", "float", "str", "bool", "list",
    "dict", "set", "tuple", "type", "isinstance", "hasattr", "getattr",
    "setattr", "sorted", "reversed", "enumerate", "zip", "map",
    "filter", "min", "max", "sum", "any", "all", "abs", "round",
    "pow", "chr", "ord", "hex", "oct", "bin", "format", "hash",
    "id", "repr", "ascii", "complex", "bytes", "bytearray",
    "frozenset", "property", "staticmethod", "slice", "super",
    "object", "iter", "next",
}


@dataclass
class SandboxResult:
    success: bool
    stdout: str
    stderr: str
    error: Optional[str] = None
    execution_time_seconds: float = 0.0


class ImportDenied(Exception):
    pass


class TimeoutError_(Exception):
    pass


class PythonSandbox:
    MAX_OUTPUT_CHARS = 50_000

    def __init__(self, timeout: Optional[int] = None):
        self.default_timeout = timeout or 30

    def execute(self, code: str, timeout: Optional[int] = None) -> SandboxResult:
        timeout = timeout or self.default_timeout

        parent_conn, child_conn = multiprocessing.Pipe(duplex=False)
        process = multiprocessing.Process(
            target=self._run_in_process,
            args=(code, child_conn),
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

    def _run_in_process(self, code: str, conn):
        try:
            self._validate_ast(code)
        except Exception as e:
            conn.send(SandboxResult(success=False, stdout="", stderr="", error=str(e)))
            return

        safe_globals = {
            "__builtins__": __builtins__,
            "__import__": self._safe_import,
            "open": self._raise_blocked,
            "exec": self._raise_blocked,
            "eval": self._raise_blocked,
            "compile": self._raise_blocked,
            "input": self._raise_blocked,
        }

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
            conn.send(SandboxResult(success=True, stdout=out, stderr=err))
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
