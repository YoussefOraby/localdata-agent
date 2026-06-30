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
