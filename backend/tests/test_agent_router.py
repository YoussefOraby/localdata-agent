from app.agent.router import _keyword_route, route_question


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
    assert len(types) <= 3


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
