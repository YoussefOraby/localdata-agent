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
    assert len(types) <= 4


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


def test_router_returns_web_search_for_search_question():
    types, explanation = route_question("search for current e-commerce trends")
    assert "web_search" in types
    assert len(types) <= 4


def test_router_returns_combined_csv_and_search():
    types, explanation = route_question("summarize this dataset and search for sales strategies")
    csv_types = {"summary", "missing_outliers", "best_worst", "basic_chart", "web_search"}
    assert all(t in csv_types for t in types)
    assert "web_search" in types or "summary" in types


def test_router_returns_summary_with_search():
    types, explanation = route_question("search for current data quality best practices")
    assert "web_search" in types

    types2, explanation2 = route_question("find missing values and search for current e-commerce growth trends")
    assert "missing_outliers" in types2 or "web_search" in types2


def test_clean_search_query_removes_csv_refs():
    from app.agent.graph import _clean_search_query
    result = _clean_search_query("Summarize this CSV and search for current trends")
    assert "this csv" not in result.lower()


def test_clean_search_query_keeps_question_intent():
    from app.agent.graph import _clean_search_query
    result = _clean_search_query("search for current e-commerce growth trends")
    assert "e-commerce" in result or "growth" in result


def test_chart_and_search_returns_both():
    types, explanation = route_question("Show me a chart and search for current e-commerce trends.")
    assert "basic_chart" in types
    assert "web_search" in types
    assert len(types) <= 4


def test_search_only_question():
    types, explanation = route_question("Search for current sales improvement strategies.")
    assert "web_search" in types


def test_summary_and_search():
    types, explanation = route_question("Summarize this dataset and search for latest market trends.")
    assert "summary" in types
    assert "web_search" in types


def test_clean_explanation_removes_dollar_signs():
    from app.agent.graph import _clean_explanation
    result = _clean_explanation("Revenue ranged from $20 to as high as $500 per item")
    assert "$" not in result
    assert "to" in result


def test_clean_explanation_adds_spaces_around_numbers():
    from app.agent.graph import _clean_explanation
    result = _clean_explanation("20toashighas500")
    assert "20 to" in result or "to as" in result or "as high" in result


def test_clean_explanation_collapses_whitespace():
    from app.agent.graph import _clean_explanation
    result = _clean_explanation("hello    world")
    assert "hello world" in result
    assert "    " not in result
