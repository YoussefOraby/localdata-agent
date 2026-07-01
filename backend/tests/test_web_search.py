from unittest.mock import patch

from app.search.web_search import WebSearchTool, SearchItem, SearchResult


class TestWebSearchToolMocked:
    def test_search_returns_results(self):
        mock_results = [
            {"title": "Result 1", "href": "https://example.com/1", "body": "Snippet one"},
            {"title": "Result 2", "href": "https://example.com/2", "body": "Snippet two"},
        ]

        with patch("duckduckgo_search.DDGS") as mock_ddgs:
            mock_instance = mock_ddgs.return_value
            mock_instance.text.return_value = mock_results

            tool = WebSearchTool(max_results=5)
            result = tool.search("test query")

        assert result.success is True
        assert result.query == "test query"
        assert len(result.results) == 2
        assert result.results[0].title == "Result 1"
        assert result.results[0].url == "https://example.com/1"
        assert result.results[0].snippet == "Snippet one"
        assert result.execution_time_seconds >= 0

    def test_search_handles_empty_results(self):
        with patch("duckduckgo_search.DDGS") as mock_ddgs:
            mock_instance = mock_ddgs.return_value
            mock_instance.text.return_value = []

            tool = WebSearchTool()
            result = tool.search("empty query")

        assert result.success is True
        assert len(result.results) == 0

    def test_search_handles_exception(self):
        with patch("duckduckgo_search.DDGS") as mock_ddgs:
            mock_instance = mock_ddgs.return_value
            mock_instance.text.side_effect = Exception("Rate limited")

            tool = WebSearchTool()
            result = tool.search("failing query")

        assert result.success is False
        assert "Rate limited" in (result.error or "")
        assert len(result.results) == 0

    def test_search_respects_max_results(self):
        mock_results = [{"title": f"R{i}", "href": f"https://example.com/{i}", "body": f"Body {i}"} for i in range(10)]

        with patch("duckduckgo_search.DDGS") as mock_ddgs:
            mock_instance = mock_ddgs.return_value
            mock_instance.text.return_value = mock_results[:3]

            tool = WebSearchTool(max_results=3)
            result = tool.search("limited query")

        assert result.success is True
        assert len(result.results) <= 3
        mock_instance.text.assert_called_once_with("limited query", max_results=3)

    def test_search_item_dataclass(self):
        item = SearchItem(title="T", url="https://t.com", snippet="S")
        assert item.title == "T"
        assert item.url == "https://t.com"
        assert item.snippet == "S"

    def test_search_result_dataclass(self):
        item = SearchItem(title="T", url="https://t.com")
        result = SearchResult(success=True, query="q", results=[item])
        assert result.success is True
        assert result.query == "q"
        assert len(result.results) == 1
