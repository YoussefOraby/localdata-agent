import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SearchItem:
    title: str
    url: str
    snippet: Optional[str] = None


@dataclass
class SearchResult:
    success: bool
    query: str
    results: list[SearchItem] = field(default_factory=list)
    error: Optional[str] = None
    execution_time_seconds: float = 0.0


class WebSearchTool:
    def __init__(self, max_results: int = 5):
        self.max_results = max_results

    def search(self, query: str, max_results: Optional[int] = None) -> SearchResult:
        start = time.monotonic()
        limit = max_results or self.max_results

        try:
            from duckduckgo_search import DDGS

            ddgs = DDGS()
            raw_results = list(ddgs.text(query, max_results=limit))
            items = []
            for r in raw_results:
                items.append(SearchItem(
                    title=r.get("title", ""),
                    url=r.get("href", ""),
                    snippet=r.get("body", None),
                ))

            elapsed = time.monotonic() - start
            logger.info("Web search for '%s' returned %d results in %.2fs", query, len(items), elapsed)
            return SearchResult(
                success=True,
                query=query,
                results=items,
                execution_time_seconds=round(elapsed, 4),
            )
        except ImportError:
            elapsed = time.monotonic() - start
            logger.warning("duckduckgo_search not installed")
            return SearchResult(
                success=False,
                query=query,
                error="duckduckgo_search package is not installed.",
                execution_time_seconds=round(elapsed, 4),
            )
        except Exception as e:
            elapsed = time.monotonic() - start
            logger.warning("Web search failed for '%s': %s", query, e)
            return SearchResult(
                success=False,
                query=query,
                error=f"Web search is temporarily unavailable: {e}",
                execution_time_seconds=round(elapsed, 4),
            )
