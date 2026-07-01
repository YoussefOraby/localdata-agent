import pytest

from app.executor.sandbox import PythonSandbox


@pytest.fixture
def sandbox():
    return PythonSandbox(timeout=10)


def test_simple_print(sandbox):
    result = sandbox.execute("print('hello world')")
    assert result.success is True
    assert result.stdout.strip() == "hello world"
    assert result.error is None


def test_math_import(sandbox):
    code = """
import math
print(math.sqrt(16))
"""
    result = sandbox.execute(code)
    assert result.success is True
    assert result.stdout.strip() == "4.0"


def test_statistics_import(sandbox):
    code = """
import statistics
data = [1, 2, 3, 4, 5]
print(statistics.mean(data))
"""
    result = sandbox.execute(code)
    assert result.success is True
    assert result.stdout.strip() == "3"


def test_pandas_import(sandbox):
    code = """
import pandas as pd
print(pd.DataFrame({'a': [1, 2]}).shape)
"""
    result = sandbox.execute(code)
    assert result.success is True
    assert "(2, 1)" in result.stdout


def test_blocked_import_os(sandbox):
    code = "import os"
    result = sandbox.execute(code)
    assert result.success is False
    assert "not allowed" in (result.error or "").lower()


def test_blocked_import_subprocess(sandbox):
    code = "import subprocess"
    result = sandbox.execute(code)
    assert result.success is False
    assert "not allowed" in (result.error or "").lower()


def test_blocked_import_sys(sandbox):
    code = "import sys"
    result = sandbox.execute(code)
    assert result.success is False
    assert "not allowed" in (result.error or "").lower()


def test_blocked_open_builtin(sandbox):
    code = "open('test.txt')"
    result = sandbox.execute(code)
    assert result.success is False


def test_blocked_eval(sandbox):
    code = "eval('1+1')"
    result = sandbox.execute(code)
    assert result.success is False


def test_timeout(sandbox):
    code = "while True: pass"
    result = sandbox.execute(code, timeout=2)
    assert result.success is False
    assert "timed out" in (result.error or "").lower()


def test_syntax_error(sandbox):
    code = "this is not valid python"
    result = sandbox.execute(code)
    assert result.success is False
    assert "syntax error" in (result.error or "").lower()


def test_stdout_capture(sandbox):
    code = """
print("line1")
print("line2")
print("line3")
"""
    result = sandbox.execute(code)
    assert result.success is True
    lines = result.stdout.strip().split("\n")
    assert len(lines) == 3
    assert lines[0] == "line1"
    assert lines[2] == "line3"


def test_json_import(sandbox):
    code = """
import json
data = {"key": "value"}
print(json.dumps(data))
"""
    result = sandbox.execute(code)
    assert result.success is True
    assert '"key": "value"' in result.stdout


def test_re_import(sandbox):
    code = """
import re
print(re.sub(r'\\d+', 'X', 'abc123def'))
"""
    result = sandbox.execute(code)
    assert result.success is True
    assert result.stdout.strip() == "abcXdef"


def test_collections_import(sandbox):
    code = """
from collections import Counter
data = Counter([1, 1, 2, 3])
print(data[1])
"""
    result = sandbox.execute(code)
    assert result.success is True
    assert result.stdout.strip() == "2"


def test_datetime_import(sandbox):
    code = """
from datetime import datetime
print(datetime.now().year)
"""
    result = sandbox.execute(code)
    assert result.success is True
    assert result.stdout.strip().isdigit()


def test_large_stdout_captured(sandbox):
    code = "result = 'x' * 500"
    result = sandbox.execute(code, timeout=10)
    assert result.success is True
    assert len(result.result) == 500


def test_context_cannot_override_security(sandbox):
    code = """
try:
    open('test.txt')
    result = False
except Exception:
    result = True
"""
    result = sandbox.execute(code, context={"open": "hacker_value"})
    assert result.success is True
    assert result.result is True, "open should be blocked even when context contains it"


def test_context_dangerous_keys_filtered(sandbox):
    code = """
try:
    eval('1+1')
    result = False
except Exception:
    result = True
"""
    result = sandbox.execute(code, context={"eval": "hacker_value"})
    assert result.success is True
    assert result.result is True, "eval should be blocked even when context contains it"


def test_blocked_exec(sandbox):
    code = "exec('x = 1')"
    result = sandbox.execute(code)
    assert result.success is False


def test_result_dict_serialized(sandbox):
    code = """
import numpy as np
result = {
    "int_val": np.int64(42),
    "float_val": np.float64(3.14),
    "bool_val": np.bool_(True),
}
"""
    sandbox2 = PythonSandbox(timeout=5)
    result = sandbox2.execute(code)
    assert result.success is True
    assert result.result["int_val"] == 42
    assert isinstance(result.result["int_val"], int)
    assert result.result["float_val"] == 3.14
    assert isinstance(result.result["float_val"], float)
    assert result.result["bool_val"] is True
    assert isinstance(result.result["bool_val"], bool)
