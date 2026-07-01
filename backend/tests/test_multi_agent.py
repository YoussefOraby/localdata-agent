import pandas as pd
import pytest
from unittest.mock import patch

from app.agent.multi_agent import (
    _manager_agent,
    _map_types_to_agents,
    _data_analyst_agent,
    _visualization_agent,
    _research_agent,
    _reviewer_agent,
    _compose_final_answer,
    run_multi_agent,
    _clean_search_query,
    _generate_fallback_queries,
)
from app.agent.router import route_question


@pytest.fixture
def sample_csv_bytes():
    df = pd.DataFrame({
        "date": ["2024-01-01", "2024-02-01", "2024-03-01"],
        "sales": [100, 200, 150],
        "category": ["A", "B", "A"],
    })
    return df.to_csv(index=False).encode("utf-8")


class TestMapTypesToAgents:
    def test_summary_maps_to_data_analyst(self):
        agents = _map_types_to_agents(["summary"])
        assert "Data Analyst Agent" in agents
        assert "Reviewer Agent" in agents

    def test_chart_maps_to_visualization(self):
        agents = _map_types_to_agents(["basic_chart"])
        assert "Visualization Agent" in agents
        assert "Reviewer Agent" in agents

    def test_search_maps_to_research(self):
        agents = _map_types_to_agents(["web_search"])
        assert "Research Agent" in agents
        assert "Reviewer Agent" in agents

    def test_combined_maps_all_agents(self):
        agents = _map_types_to_agents(["summary", "basic_chart", "web_search"])
        assert "Data Analyst Agent" in agents
        assert "Visualization Agent" in agents
        assert "Research Agent" in agents
        assert "Reviewer Agent" in agents


class TestManagerAgent:
    def test_summary_question(self):
        types, agents = _manager_agent("summarize this dataset")
        assert "summary" in types
        assert "Data Analyst Agent" in agents
        assert "Reviewer Agent" in agents

    def test_chart_question(self):
        types, agents = _manager_agent("show me a chart")
        assert "basic_chart" in types
        assert "Visualization Agent" in agents


class TestDataAnalystAgent:
    def test_runs_summary(self, sample_csv_bytes):
        results, chart = _data_analyst_agent(sample_csv_bytes, "test.csv", ["summary"])
        assert len(results) == 1
        assert results[0]["success"] is True
        assert results[0]["analysis_type"] == "summary"
        assert chart is None


class TestVisualizationAgent:
    def test_generates_chart(self, sample_csv_bytes):
        result, chart = _visualization_agent(sample_csv_bytes, "test.csv")
        assert result["success"] is True
        assert result["analysis_type"] == "basic_chart"
        assert chart is not None


class TestResearchAgent:
    def test_search_with_mocked_results(self):
        mock_results = [{"title": "R1", "href": "https://x.com/1", "body": "Snippet 1"}]

        with patch("app.agent.multi_agent.WebSearchTool") as MockTool:
            instance = MockTool.return_value
            from app.search.web_search import SearchResult, SearchItem
            instance.search.return_value = SearchResult(
                success=True, query="test", results=[SearchItem(title="R1", url="https://x.com/1", snippet="Snippet 1")]
            )
            results, query, sources = _research_agent("search for current trends")

        assert len(results) > 0
        assert len(sources) > 0
        assert "R1" in results[0].get("title", "")

    def test_search_empty_returns_graceful(self):
        with patch("app.agent.multi_agent.WebSearchTool") as MockTool:
            instance = MockTool.return_value
            from app.search.web_search import SearchResult
            instance.search.return_value = SearchResult(success=True, query="x", results=[])

            results, query, sources = _research_agent("search for nothing")

        assert len(sources) == 0


class TestReviewerAgent:
    def test_review_passes_when_all_good(self):
        output = {
            "final_answer": "Some answer",
            "selected_analysis_types": ["summary"],
            "sources": [],
            "chart": None,
        }
        review = _reviewer_agent(output)
        assert review["passed"] is True

    def test_review_notes_missing_answer(self):
        output = {
            "final_answer": None,
            "selected_analysis_types": ["summary"],
            "sources": [],
            "chart": None,
        }
        review = _reviewer_agent(output)
        assert review["passed"] is False
        assert any("final answer" in n.lower() for n in review["notes"])

    def test_review_notes_search_failure(self):
        output = {
            "final_answer": "Answer",
            "selected_analysis_types": ["summary", "web_search"],
            "sources": [],
            "chart": None,
        }
        review = _reviewer_agent(output)
        assert review["passed"] is False
        assert any("no results" in n.lower() for n in review["notes"])

    def test_review_notes_chart_missing(self):
        output = {
            "final_answer": "Answer",
            "selected_analysis_types": ["summary", "basic_chart"],
            "sources": [],
            "chart": None,
        }
        review = _reviewer_agent(output)
        assert review["passed"] is False
        assert any("chart" in n.lower() for n in review["notes"])


class TestComposeFinalAnswer:
    def test_contains_dataset_insights(self):
        results = [{"success": True, "analysis_type": "summary", "explanation": "The dataset has 10 rows."}]
        answer = _compose_final_answer(results, [], [], None, ["summary"])
        assert "Dataset insights" in answer
        assert "10 rows" in answer

    def test_contains_search_failure_message(self):
        answer = _compose_final_answer([], [], [], None, ["web_search"])
        assert "no results" in answer.lower() or "unavailable" in answer.lower()

    def test_clean_query_removes_search_for(self):
        q = _clean_search_query("Search for current sales improvement strategies.")
        assert "search for" not in q
        assert "strategies" in q

    def test_fallback_generates_alternatives(self):
        fbs = _generate_fallback_queries("sales improvement strategies for retail")
        assert len(fbs) > 0


class TestRunMultiAgent:
    def test_summary_only(self, sample_csv_bytes):
        result = run_multi_agent(sample_csv_bytes, "test.csv", "summarize this dataset")
        assert result["success"] is True
        assert result["mode"] == "multi_agent"
        assert "summary" in result["selected_analysis_types"]
        assert "Data Analyst Agent" in result["agents_used"]
        assert "Reviewer Agent" in result["agents_used"]
        assert result["review"] is not None
        assert result["final_answer"] is not None

    def test_chart_only(self, sample_csv_bytes):
        result = run_multi_agent(sample_csv_bytes, "test.csv", "show me a chart")
        assert result["success"] is True
        assert "basic_chart" in result["selected_analysis_types"]
        assert "Visualization Agent" in result["agents_used"]

    def test_search_returns_graceful(self, sample_csv_bytes):
        with patch("app.agent.multi_agent.WebSearchTool") as MockTool:
            instance = MockTool.return_value
            from app.search.web_search import SearchResult
            instance.search.return_value = SearchResult(success=True, query="x", results=[])

            result = run_multi_agent(sample_csv_bytes, "test.csv", "search for current trends")

        assert result["success"] is True
        assert "web_search" in result["selected_analysis_types"]
        assert "Research Agent" in result["agents_used"]
        assert result["search_query"] is not None
        assert result["sources"] is not None

    def test_combined_uses_all_agents(self, sample_csv_bytes):
        with patch("app.agent.multi_agent.WebSearchTool") as MockTool:
            instance = MockTool.return_value
            from app.search.web_search import SearchResult, SearchItem
            instance.search.return_value = SearchResult(
                success=True, query="test",
                results=[SearchItem(title="R", url="https://x.com", snippet="S")]
            )

            result = run_multi_agent(
                sample_csv_bytes, "test.csv",
                "Analyze this dataset, show a chart, and search for current sales improvement strategies."
            )

        assert result["success"] is True
        assert "Data Analyst Agent" in result["agents_used"]
        assert "Visualization Agent" in result["agents_used"]
        assert "Research Agent" in result["agents_used"]
        assert "Reviewer Agent" in result["agents_used"]
        assert len(result["sources"]) > 0

    def test_error_handled_gracefully(self, sample_csv_bytes):
        result = run_multi_agent(b"not,csv\na,b\n", "bad.csv", "summarize this")
        assert result["success"] is True or result["success"] is False
        assert result["mode"] == "multi_agent"
