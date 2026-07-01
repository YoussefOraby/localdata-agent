import logging
import re
import time
from typing import Optional

from app.agent.router import route_question
from app.analysis.csv_analyzer import CSVAnalyzer
from app.llm.ollama_client import OllamaClient
from app.search.web_search import WebSearchTool

logger = logging.getLogger(__name__)

CSV_ANALYSIS_TYPES = {"summary", "missing_outliers", "best_worst"}
DEFAULT_TIMEOUT = 180


def _clean_search_query(question: str) -> str:
    q = question.lower()
    for phrase in ["this csv", "this dataset", "this data", "uploaded file", "my csv", "my dataset"]:
        q = q.replace(phrase, "")
    search_markers = ["search for", "look up", "find", "search"]
    for marker in sorted(search_markers, key=len, reverse=True):
        if marker in q:
            idx = q.index(marker) + len(marker)
            q = q[idx:].strip()
            break
    q = re.sub(r"^(current|recent|latest|online|web|the)\s+", "", q)
    q = re.sub(r"\s+", " ", q).strip()
    q = q.strip(".,!?;:-").strip()
    return q if q else question


def _generate_fallback_queries(query: str) -> list[str]:
    words = query.split()
    fallbacks = []
    if len(words) > 3:
        fallbacks.append(" ".join(words[1:]))
        fallbacks.append(" ".join(words[-3:]))
    if len(words) > 2:
        fallbacks.append(" ".join(words[-2:]))
    seen = set()
    unique = []
    for f in fallbacks:
        if f not in seen and f != query:
            seen.add(f)
            unique.append(f)
    return unique[:3]


def _clean_explanation(text: str) -> str:
    text = re.sub(r"\$", "", text)
    text = re.sub(r"(?<=\d)(?=[a-zA-Z])", " ", text)
    text = re.sub(r"(?<=[a-zA-Z])(?=\d)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _map_types_to_agents(analysis_types: list[str]) -> list[str]:
    agents = []
    csv_types = [t for t in analysis_types if t in CSV_ANALYSIS_TYPES]
    if csv_types:
        agents.append("Data Analyst Agent")
    if "basic_chart" in analysis_types:
        agents.append("Visualization Agent")
    if "web_search" in analysis_types:
        agents.append("Research Agent")
    agents.append("Reviewer Agent")
    return agents


def _manager_agent(question: str, llm: Optional[OllamaClient] = None) -> tuple[list[str], list[str]]:
    types, _ = route_question(question, llm)
    agents = _map_types_to_agents(types)
    return types, agents


def _data_analyst_agent(file_bytes: bytes, file_name: str, analysis_types: list[str]) -> tuple[list[dict], Optional[dict]]:
    analyzer = CSVAnalyzer()
    results = []
    chart = None
    for atype in analysis_types:
        if atype in CSV_ANALYSIS_TYPES:
            try:
                r = analyzer.analyze(file_bytes, file_name, atype)
                r["analysis_type"] = atype
                results.append(r)
            except Exception as e:
                logger.error("Data Analyst Agent: %s failed: %s", atype, e)
                results.append({"success": False, "analysis_type": atype, "error": str(e)})
    return results, chart


def _visualization_agent(file_bytes: bytes, file_name: str) -> tuple[Optional[dict], Optional[dict]]:
    analyzer = CSVAnalyzer()
    try:
        r = analyzer.analyze(file_bytes, file_name, "basic_chart")
        r["analysis_type"] = "basic_chart"
        chart = r.get("chart")
        return r, chart
    except Exception as e:
        logger.error("Visualization Agent failed: %s", e)
        return {"success": False, "analysis_type": "basic_chart", "error": str(e)}, None


def _research_agent(question: str) -> tuple[list[dict], Optional[str], list[dict]]:
    search_query = _clean_search_query(question)
    queries_to_try = [search_query] + _generate_fallback_queries(search_query)
    tool = WebSearchTool()
    search_results = []
    sources = []
    final_query = search_query

    for attempt, q in enumerate(queries_to_try):
        sr = tool.search(q)
        if sr.success and sr.results:
            for item in sr.results:
                entry = {"title": item.title, "url": item.url, "snippet": item.snippet}
                search_results.append(entry)
                sources.append(entry)
            final_query = q
            break
        elif sr.success and not sr.results and attempt == len(queries_to_try) - 1:
            pass
        elif not sr.success and attempt == len(queries_to_try) - 1:
            search_results.append({"error": sr.error or "Web search failed"})
        continue

    return search_results, final_query, sources


def _reviewer_agent(output: dict) -> dict:
    checks = {
        "has_answer": bool(output.get("final_answer")),
        "has_selected_tools": bool(output.get("selected_analysis_types")),
        "search_handled": True,
        "charts_handled": True,
    }
    notes = []

    if not checks["has_answer"]:
        notes.append("No final answer was produced.")
    if not checks["has_selected_tools"]:
        notes.append("No analysis tools were selected.")

    analysis_types = output.get("selected_analysis_types", [])
    if "web_search" in analysis_types:
        sources = output.get("sources", [])
        if not sources:
            checks["search_handled"] = False
            notes.append("Web search was requested but returned no results.")

    if "basic_chart" in analysis_types:
        chart = output.get("chart")
        if not chart:
            checks["charts_handled"] = False
            notes.append("Chart was requested but none was produced.")

    passed = all(checks.values())
    return {"passed": passed, "checks": checks, "notes": notes}


def _compose_final_answer(results: list[dict], search_results: list[dict], sources: list[dict],
                          search_query: Optional[str], analysis_types: list[str]) -> str:
    lines = []

    csv_results = [r for r in results if r.get("analysis_type") in CSV_ANALYSIS_TYPES]
    viz_result = next((r for r in results if r.get("analysis_type") == "basic_chart"), None)
    if not viz_result:
        viz_result = next((r for r in results if r.get("analysis_type") == "basic_chart"), None)

    if csv_results or viz_result:
        lines.append("**Dataset insights**")
        for r in results:
            if r.get("success") and r.get("explanation"):
                clean = _clean_explanation(r["explanation"])
                lines.append(f"- {clean}")
            elif not r.get("success"):
                atype = r.get("analysis_type", "unknown")
                err = r.get("error", "unknown error")
                lines.append(f"- {atype} analysis failed: {err}")

    valid_search = [r for r in search_results if "error" not in r]
    has_search_error = any("error" in r for r in search_results) if search_results else False

    if valid_search:
        lines.append("")
        lines.append("**Web context**")
        for r in valid_search[:3]:
            snippet = (r.get("snippet") or "")[:200]
            snippet = _clean_explanation(snippet)
            lines.append(f"- {r.get('title', '')}: {snippet}")

        if search_query:
            lines.append("")
            lines.append(f"*Search query used: `{search_query}`*")

    search_used = "web_search" in analysis_types
    if search_used and not valid_search:
        lines.append("")
        if has_search_error:
            lines.append("*Web search was unavailable, so the answer is based only on the uploaded CSV.*")
        else:
            lines.append("*Web search returned no results. Try a broader question.*")

    if sources:
        lines.append("")
        lines.append("**Sources**")
        for src in sources:
            title = src.get("title", "Untitled")
            url = src.get("url", "")
            lines.append(f"- [{title}]({url})")

    return "\n\n".join(lines) if lines else "Analysis completed with no findings."


def run_multi_agent(file_bytes: bytes, file_name: str, question: str, llm: Optional[OllamaClient] = None) -> dict:
    start = time.monotonic()
    all_steps = []
    all_results = []
    chart = None
    search_results = []
    search_query = None
    sources = []

    try:
        all_steps.append("Running Manager Agent")
        analysis_types, agents_used = _manager_agent(question, llm)
        all_steps.append(f"Manager Agent: selected {', '.join(analysis_types)}, agents: {', '.join(agents_used)}")

        csv_types = [t for t in analysis_types if t in CSV_ANALYSIS_TYPES]
        if csv_types:
            all_steps.append("Running Data Analyst Agent")
            csv_results, _ = _data_analyst_agent(file_bytes, file_name, csv_types)
            all_results.extend(csv_results)
            all_steps.append(f"Data Analyst Agent: completed {len(csv_results)} analyses")

        if "basic_chart" in analysis_types:
            all_steps.append("Running Visualization Agent")
            viz_result, viz_chart = _visualization_agent(file_bytes, file_name)
            all_results.append(viz_result)
            if viz_chart:
                chart = viz_chart
                all_steps.append("Visualization Agent: chart generated")
            else:
                all_steps.append("Visualization Agent: chart not available")

        if "web_search" in analysis_types:
            all_steps.append("Running Research Agent")
            search_results, search_query, sources = _research_agent(question)
            if sources:
                all_steps.append(f"Research Agent: found {len(sources)} results")
            else:
                all_steps.append("Research Agent: no results found")
            if search_query:
                all_steps.append(f"Research Agent: query '{search_query}'")

        final_answer = _compose_final_answer(all_results, search_results, sources, search_query, analysis_types)
        all_steps.append("Composing final answer")

        output = {
            "selected_analysis_types": analysis_types,
            "results": all_results,
            "chart": chart,
            "search_results": search_results,
            "search_query": search_query,
            "sources": sources,
            "final_answer": final_answer,
        }

        all_steps.append("Running Reviewer Agent")
        review = _reviewer_agent(output)
        if review["passed"]:
            all_steps.append("Reviewer Agent: all checks passed")
        else:
            all_steps.append(f"Reviewer Agent: issues found — {'; '.join(review['notes'])}")

        elapsed = time.monotonic() - start

        return {
            "success": True,
            "mode": "multi_agent",
            "question": question,
            "file_name": file_name,
            "agents_used": agents_used,
            "selected_analysis_types": analysis_types,
            "results": all_results,
            "final_answer": final_answer,
            "chart": chart,
            "sources": sources,
            "search_query": search_query,
            "review": review,
            "steps": all_steps,
            "error": None,
            "execution_time_seconds": round(elapsed, 4),
        }

    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("Multi-agent run failed: %s", e)
        return {
            "success": False,
            "mode": "multi_agent",
            "question": question,
            "file_name": file_name,
            "agents_used": [],
            "selected_analysis_types": [],
            "results": [],
            "final_answer": None,
            "chart": None,
            "sources": [],
            "search_query": None,
            "review": None,
            "steps": all_steps + [f"Multi-agent error: {e}"],
            "error": str(e),
            "execution_time_seconds": round(elapsed, 4),
        }
