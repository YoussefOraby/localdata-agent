import logging
import re
import time

from langgraph.graph import END, StateGraph

from app.agent.router import route_question
from app.agent.state import AgentState
from app.analysis.csv_analyzer import CSVAnalyzer
from app.llm.ollama_client import OllamaClient
from app.search.web_search import WebSearchTool

logger = logging.getLogger(__name__)


def _clean_search_query(question: str) -> str:
    q = question.lower()
    for phrase in ["this csv", "this dataset", "this data", "uploaded file", "my csv", "my dataset"]:
        q = q.replace(phrase, "")
    q = q.strip().strip(".,!?;:").strip()
    return q if q else question


def _route_question_node(state: AgentState) -> dict:
    llm = OllamaClient()
    types, explanation = route_question(state.question, llm)
    steps = state.steps[:]
    steps.append(f"Analyzing question: selected {', '.join(types)}")

    return {
        "selected_analysis_types": types,
        "steps": steps,
    }


def _run_analyses(state: AgentState) -> dict:
    analyzer = CSVAnalyzer()
    results = []
    steps = state.steps[:]
    all_charts = []
    search_results = []
    search_query = None
    sources = []

    for atype in state.selected_analysis_types:
        if atype == "web_search":
            search_query = _clean_search_query(state.question)
            steps.append(f"Searching web for: {search_query}")
            tool = WebSearchTool()
            sr = tool.search(search_query)
            if sr.success:
                for item in sr.results:
                    search_results.append({
                        "title": item.title,
                        "url": item.url,
                        "snippet": item.snippet,
                    })
                    sources.append({
                        "title": item.title,
                        "url": item.url,
                        "snippet": item.snippet,
                    })
                steps.append(f"Found {len(sr.results)} web results")
            else:
                search_results.append({"error": sr.error or "Web search failed"})
                steps.append(f"Web search unavailable: {sr.error}")
            continue

        try:
            steps.append(f"Running {atype} analysis")
            r = analyzer.analyze(state.file_bytes, state.file_name, atype)
            r["analysis_type"] = atype
            results.append(r)
            if r.get("success") and r.get("chart"):
                all_charts.append(r["chart"])
        except Exception as e:
            logger.error("Analysis %s failed: %s", atype, e)
            results.append({
                "success": False,
                "analysis_type": atype,
                "error": str(e),
            })

    chart = all_charts[0] if all_charts else None

    return {
        "results": results,
        "steps": steps,
        "search_results": search_results,
        "search_query": search_query,
        "sources": sources,
    }


def _clean_explanation(text: str) -> str:
    text = re.sub(r"\$", "", text)
    text = re.sub(r"(?<=\d)(?=[a-zA-Z])", " ", text)
    text = re.sub(r"(?<=[a-zA-Z])(?=\d)", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _compose_answer(state: AgentState) -> dict:
    steps = state.steps[:]

    if state.error:
        return {"final_answer": f"Analysis failed: {state.error}", "steps": steps}

    if not state.results and not state.search_results:
        return {"final_answer": "No analysis results were produced.", "steps": steps}

    lines = []
    has_dataset_insights = bool(state.results)

    if has_dataset_insights:
        lines.append("**Dataset insights**")
        for r in state.results:
            if r.get("success"):
                explanation = r.get("explanation", "")
                if explanation:
                    clean = _clean_explanation(explanation)
                    lines.append(f"- {clean}")
            else:
                atype = r.get("analysis_type", "unknown")
                err = r.get("error", "unknown error")
                lines.append(f"- {atype} analysis failed: {err}")

    valid_results = []
    if state.search_results:
        valid_results = [r for r in state.search_results if "error" not in r]

    if valid_results:
        lines.append("")
        lines.append("**Web context**")
        for r in valid_results[:3]:
            snippet = (r.get("snippet") or "")[:200]
            snippet = _clean_explanation(snippet)
            lines.append(f"- {r.get('title', '')}: {snippet}")

        if state.search_query:
            lines.append("")
            lines.append(f"*Search query used: `{state.search_query}`*")

    search_used = "web_search" in (state.selected_analysis_types or [])
    if search_used and not valid_results:
        lines.append("")
        lines.append("*Web search was unavailable, so the answer is based only on the uploaded CSV.*")

    if state.sources:
        lines.append("")
        lines.append("**Sources**")
        for src in state.sources:
            title = src.get("title", "Untitled")
            url = src.get("url", "")
            lines.append(f"- [{title}]({url})")

    answer = "\n\n".join(lines) if lines else "Analysis completed with no findings."
    steps.append("Composing final answer")

    return {"final_answer": answer, "steps": steps}


def build_agent() -> StateGraph:
    workflow = StateGraph(AgentState)

    workflow.add_node("route_question", _route_question_node)
    workflow.add_node("run_selected_analyses", _run_analyses)
    workflow.add_node("compose_final_answer", _compose_answer)

    workflow.set_entry_point("route_question")

    workflow.add_edge("route_question", "run_selected_analyses")
    workflow.add_edge("run_selected_analyses", "compose_final_answer")
    workflow.add_edge("compose_final_answer", END)

    return workflow.compile()


def run_agent(file_bytes: bytes, file_name: str, question: str) -> dict:
    start = time.monotonic()

    state = AgentState(
        question=question,
        file_bytes=file_bytes,
        file_name=file_name,
    )

    try:
        agent = build_agent()
        final_state = agent.invoke(state)
        elapsed = time.monotonic() - start

        results = final_state.get("results", [])
        chart = None
        for r in results:
            if isinstance(r, dict) and r.get("chart"):
                chart = r["chart"]
                break

        return {
            "success": True,
            "question": question,
            "file_name": file_name,
            "selected_analysis_types": final_state.get("selected_analysis_types", []),
            "results": results,
            "search_results": final_state.get("search_results", []),
            "search_query": final_state.get("search_query"),
            "sources": final_state.get("sources", []),
            "final_answer": final_state.get("final_answer"),
            "chart": chart,
            "steps": final_state.get("steps", []),
            "error": None,
            "execution_time_seconds": round(elapsed, 4),
        }
    except Exception as e:
        elapsed = time.monotonic() - start
        logger.error("Agent run failed: %s", e)
        return {
            "success": False,
            "question": question,
            "file_name": file_name,
            "selected_analysis_types": [],
            "results": [],
            "search_results": [],
            "search_query": None,
            "sources": [],
            "final_answer": None,
            "chart": None,
            "steps": [f"Agent error: {e}"],
            "error": str(e),
            "execution_time_seconds": round(elapsed, 4),
        }
