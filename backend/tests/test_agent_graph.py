import pandas as pd
import pytest

from app.agent.router import route_question


@pytest.fixture
def sample_csv_bytes():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "2024-05-01"],
        "sales": [100, 200, 150, 300, 250],
        "category": ["A", "B", "A", "B", "A"],
    })
    return df.to_csv(index=False).encode("utf-8")


def test_router_returns_summary_for_general_question():
    types, explanation = route_question("summarize this dataset")
    assert "summary" in types
    assert len(types) <= 3


def test_router_returns_missing_outliers_for_quality_question():
    types, explanation = route_question("are there any missing values or data quality issues")
    assert "missing_outliers" in types


def test_router_returns_best_worst_for_extremes():
    types, explanation = route_question("show best and worst values")
    assert "best_worst" in types


def test_router_returns_chart_for_visualization():
    types, explanation = route_question("visualize the data as a chart")
    assert "basic_chart" in types


def test_router_multiple_types():
    types, explanation = route_question("summarize and show me a chart")
    matched = {"summary", "basic_chart"}
    assert matched.issubset(set(types))
    assert len(types) <= 3


def test_router_fallback_to_summary():
    types, explanation = route_question("what is this data about")
    assert types == ["summary"]


def test_router_works_without_ollama():
    types, explanation = route_question("show missing values")
    assert "missing_outliers" in types


def test_agent_endpoint_via_csv_analyzer(sample_csv_bytes):
    from app.analysis.csv_analyzer import CSVAnalyzer
    analyzer = CSVAnalyzer()
    result = analyzer.analyze(sample_csv_bytes, "test.csv", "summary")
    assert result["success"] is True
    assert result["rows"] == 5


def test_agent_runs_multiple_analyses(sample_csv_bytes):
    from app.analysis.csv_analyzer import CSVAnalyzer
    analyzer = CSVAnalyzer()
    for atype in ("summary", "missing_outliers", "best_worst", "basic_chart"):
        result = analyzer.analyze(sample_csv_bytes, "test.csv", atype)
        assert result["success"] is True, f"{atype} failed"
