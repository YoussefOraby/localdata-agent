import os
import tempfile

import pandas as pd
import pytest

from app.analysis.csv_analyzer import CSVAnalyzer


@pytest.fixture
def sample_csv_bytes():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"],
        "sales": [100, 200, 150, 300, 250],
        "category": ["A", "B", "A", "B", "A"],
        "region": ["North", "South", "North", "South", "North"],
    })
    return df.to_csv(index=False).encode("utf-8")


@pytest.fixture
def sample_csv_with_missing_bytes():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-02-01", None, "2024-04-01", "2024-05-01"],
        "sales": [100, None, 150, 300, 250],
        "category": ["A", "B", "A", None, "A"],
    })
    return df.to_csv(index=False).encode("utf-8")


@pytest.fixture
def sample_csv_no_numeric_bytes():
    df = pd.DataFrame({
        "name": ["Alice", "Bob", "Charlie", "Diana", "Eve"],
        "city": ["NYC", "LA", "Chicago", "NYC", "LA"],
    })
    return df.to_csv(index=False).encode("utf-8")


@pytest.fixture
def analyzer():
    return CSVAnalyzer()


def test_summary_analysis(analyzer, sample_csv_bytes):
    result = analyzer.analyze(sample_csv_bytes, "test.csv", "summary")
    assert result["success"] is True
    assert result["rows"] == 5
    assert result["columns"] == 4
    assert result["analysis_type"] == "summary"
    assert result["result"] is not None
    assert "metrics" in result["result"]
    assert result["result"]["metrics"]["rows"] == 5
    assert len(result["steps"]) > 0


def test_missing_outliers(analyzer, sample_csv_with_missing_bytes):
    result = analyzer.analyze(sample_csv_with_missing_bytes, "test.csv", "missing_outliers")
    assert result["success"] is True
    assert result["result"] is not None
    tables = result["result"].get("tables", {})
    assert "missing_values" in tables
    assert len(tables["missing_values"]) > 0


def test_best_worst(analyzer, sample_csv_bytes):
    result = analyzer.analyze(sample_csv_bytes, "test.csv", "best_worst")
    assert result["success"] is True
    assert result["result"] is not None
    tables = result["result"].get("tables", {})
    assert "columns" in tables
    assert "sales" in tables["columns"]


def test_basic_chart(analyzer, sample_csv_bytes):
    result = analyzer.analyze(sample_csv_bytes, "test.csv", "basic_chart")
    assert result["success"] is True
    chart = result.get("chart")
    assert chart is not None
    assert chart["type"] in ("bar", "line")


def test_invalid_csv_returns_error(analyzer):
    bad_bytes = b"col\n" + b'"unclosed'
    result = analyzer.analyze(bad_bytes, "bad.csv", "summary")
    assert result["success"] is False


def test_empty_csv_returns_error(analyzer):
    empty_bytes = b""
    result = analyzer.analyze(empty_bytes, "empty.csv", "summary")
    assert result["success"] is False


def test_no_numeric_columns_best_worst(analyzer, sample_csv_no_numeric_bytes):
    result = analyzer.analyze(sample_csv_no_numeric_bytes, "test.csv", "best_worst")
    assert result["success"] is True
    insights = result["result"].get("insights", [])
    assert any("No numeric" in i for i in insights)


def test_no_numeric_columns_chart(analyzer, sample_csv_no_numeric_bytes):
    result = analyzer.analyze(sample_csv_no_numeric_bytes, "test.csv", "basic_chart")
    assert result["success"] is True
    chart = result.get("chart")
    assert chart is None or chart.get("type") is None


def test_analyze_creates_steps(analyzer, sample_csv_bytes):
    result = analyzer.analyze(sample_csv_bytes, "test.csv", "summary")
    assert len(result["steps"]) >= 3
    assert result["steps"][0] == "Reading CSV file"
    assert result["steps"][-1] == "Analysis completed"


def test_unknown_analysis_type(analyzer, sample_csv_bytes):
    result = analyzer.analyze(sample_csv_bytes, "test.csv", "unknown_type")
    assert result["success"] is False
    assert "Unknown analysis type" in (result["error"] or "")
