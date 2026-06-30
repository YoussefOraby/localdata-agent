import logging
import time

from langgraph.graph import END, StateGraph

from app.agent.router import route_question
from app.agent.state import AgentState
from app.analysis.csv_analyzer import CSVAnalyzer
from app.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


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

    for atype in state.selected_analysis_types:
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
    }


def _compose_answer(state: AgentState) -> dict:
    steps = state.steps[:]

    if state.error:
        return {"final_answer": f"Analysis failed: {state.error}", "steps": steps}

    if not state.results:
        return {"final_answer": "No analysis results were produced.", "steps": steps}

    lines = []
    for r in state.results:
        if r.get("success"):
            explanation = r.get("explanation", "")
            if explanation:
                lines.append(explanation)
        else:
            atype = r.get("analysis_type", "unknown")
            err = r.get("error", "unknown error")
            lines.append(f"{atype} analysis failed: {err}")

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
            "final_answer": None,
            "chart": None,
            "steps": [f"Agent error: {e}"],
            "error": str(e),
            "execution_time_seconds": round(elapsed, 4),
        }
