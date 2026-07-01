from app.agent.router import _keyword_route, route_question, _merge_types


def test_keyword_routes_summary():
    types, explanation = _keyword_route("summarize this dataset")
    assert "summary" in types
    assert isinstance(explanation, str)


def test_keyword_routes_missing_outliers():
    types, explanation = _keyword_route("find missing values and outliers")
    assert "missing_outliers" in types
    assert isinstance(explanation, str)


def test_keyword_routes_best_worst():
    types, explanation = _keyword_route("what were the best and worst months")
    assert "best_worst" in types
    assert isinstance(explanation, str)


def test_keyword_routes_basic_chart():
    types, explanation = _keyword_route("show me a chart or plot")
    assert "basic_chart" in types
    assert isinstance(explanation, str)


def test_multiple_intents_return_multiple_types():
    types, explanation = _keyword_route("summarize and find missing values")
    assert "summary" in types
    assert "missing_outliers" in types
    assert len(types) <= 3


def test_unknown_question_falls_back_to_summary():
    types, explanation = _keyword_route("hello world this is a test")
    assert types == ["summary"]
    assert isinstance(explanation, str)


def test_max_types_limit():
    types, explanation = _keyword_route(
        "summarize show chart missing values best worst"
    )
    assert len(types) <= 4


def test_keyword_routes_web_search():
    types, explanation = _keyword_route("search for recent e-commerce trends")
    assert "web_search" in types
    assert isinstance(explanation, str)


def test_keyword_routes_web_search_latest():
    types, explanation = _keyword_route("find latest strategies for sales improvement")
    assert "web_search" in types


def test_keyword_routes_combined_csv_and_search():
    types, explanation = _keyword_route("summarize and search for current market trends")
    assert "summary" in types
    assert "web_search" in types
    assert len(types) <= 4


def test_keyword_routes_search_only():
    types, explanation = _keyword_route("search the web for external information")
    assert "web_search" in types


def test_keyword_routes_search_with_chart():
    types, explanation = _keyword_route("visualize this and search for current trends")
    assert "basic_chart" in types and "web_search" in types


def test_route_question_no_llm_web_search():
    types, explanation = _keyword_route("search for current e-commerce growth trends")
    assert "web_search" in types


def test_chart_and_search_question():
    types, explanation = _keyword_route("Show me a chart and search for current e-commerce trends.")
    assert "basic_chart" in types, f"Expected basic_chart in {types}"
    assert "web_search" in types, f"Expected web_search in {types}"


def test_merge_types_adds_missing():
    merged = _merge_types(["summary"], ["web_search"])
    assert "summary" in merged
    assert "web_search" in merged


def test_merge_types_dedups():
    merged = _merge_types(["summary", "basic_chart"], ["summary", "web_search"])
    assert merged == ["summary", "basic_chart", "web_search"]


def test_merge_types_preserves_canonical_order():
    merged = _merge_types(["best_worst"], ["web_search", "summary"])
    assert merged.index("summary") < merged.index("best_worst")
    assert merged.index("best_worst") < merged.index("web_search")


def test_route_question_no_llm():
    types, explanation = route_question("summarize the data")
    assert "summary" in types
    assert isinstance(explanation, str)


def test_route_question_no_llm_missing():
    types, explanation = route_question("any missing values")
    assert "missing_outliers" in types


def test_route_question_no_llm_chart():
    types, explanation = route_question("show a chart")
    assert "basic_chart" in types


def test_route_question_chart_and_search():
    types, explanation = route_question("Show me a chart and search for current e-commerce trends.")
    assert "basic_chart" in types
    assert "web_search" in types


def test_route_question_summary_without_search():
    types, explanation = route_question("Summarize this dataset.")
    assert "summary" in types
    assert "web_search" not in types


def test_route_question_summary_and_search():
    types, explanation = route_question("Summarize this dataset and search for latest market trends.")
    assert "summary" in types
    assert "web_search" in types
