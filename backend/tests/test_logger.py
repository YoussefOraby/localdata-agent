import json
import os
import tempfile

import pytest

from app.logs.logger import JSONLLogger


@pytest.fixture
def temp_log_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


def test_logger_creates_directory(temp_log_dir):
    logger = JSONLLogger(log_dir=temp_log_dir)
    assert os.path.isdir(temp_log_dir)


def test_logger_writes_jsonl(temp_log_dir):
    logger = JSONLLogger(log_dir=temp_log_dir)
    data = {
        "file_name": "test.csv",
        "analysis_type": "summary",
        "rows": 100,
        "columns": 5,
        "success": True,
        "error": None,
        "execution_time_seconds": 1.23,
    }
    logger.log_run(data)
    assert os.path.isfile(logger.log_path)

    with open(logger.log_path, "r") as f:
        lines = f.readlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["file_name"] == "test.csv"
    assert entry["analysis_type"] == "summary"
    assert entry["success"] is True
    assert entry["rows"] == 100
    assert "timestamp" in entry


def test_logger_appends_multiple_entries(temp_log_dir):
    logger = JSONLLogger(log_dir=temp_log_dir)
    for i in range(3):
        logger.log_run({"file_name": f"file{i}.csv", "analysis_type": "summary", "success": True})
    with open(logger.log_path, "r") as f:
        lines = f.readlines()
    assert len(lines) == 3


def test_logger_get_recent_runs(temp_log_dir):
    logger = JSONLLogger(log_dir=temp_log_dir)
    for i in range(5):
        logger.log_run({"file_name": f"file{i}.csv", "analysis_type": "summary", "success": True})
    recent = logger.get_recent_runs(limit=3)
    assert len(recent) == 3
    assert recent[0]["file_name"] == "file2.csv"
    assert recent[-1]["file_name"] == "file4.csv"


def test_logger_get_recent_runs_empty(temp_log_dir):
    logger = JSONLLogger(log_dir=temp_log_dir)
    recent = logger.get_recent_runs()
    assert recent == []


def test_logger_handles_none_fields(temp_log_dir):
    logger = JSONLLogger(log_dir=temp_log_dir)
    data = {
        "file_name": None,
        "analysis_type": "summary",
        "rows": None,
        "columns": None,
        "success": False,
        "error": "Something went wrong",
        "execution_time_seconds": None,
    }
    logger.log_run(data)
    with open(logger.log_path, "r") as f:
        entry = json.loads(f.readline())
    assert entry["error"] == "Something went wrong"
    assert entry["file_name"] is None
