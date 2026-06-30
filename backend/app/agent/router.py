import json
import logging
import re
from typing import Optional

from app.agent.prompts import ROUTER_PROMPT
from app.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)

ALLOWED_TYPES = {"summary", "missing_outliers", "best_worst", "basic_chart"}
MAX_TYPES = 3

KEYWORD_RULES = [
    ({"best", "worst", "highest", "lowest", "max", "min", "top", "bottom", "extreme", "peak", "record"}, "best_worst"),
    ({"chart", "plot", "visualize", "trend", "graph", "visual", "visualization", "distribution"}, "basic_chart"),
    ({"missing", "null", "empty", "outlier", "data quality", "completeness", "gaps", "nan", "blank", "incomplete"}, "missing_outliers"),
    ({"summarize", "summary", "overview", "describe", "describe", "general", "show me"}, "summary"),
]


def route_question(question: str, llm_client: Optional[OllamaClient] = None) -> tuple[list[str], str]:
    if llm_client and llm_client.is_available():
        result = _try_llm_route(question, llm_client)
        if result is not None:
            return result

    return _keyword_route(question)


def _try_llm_route(question: str, llm_client: OllamaClient):
    try:
        prompt = ROUTER_PROMPT + question
        response = llm_client.generate(prompt)

        if response.startswith("Error"):
            return None

        parsed = _parse_llm_response(response)
        if parsed is not None:
            return parsed
    except Exception as e:
        logger.debug("LLM routing failed: %s", e)

    return None


def _parse_llm_response(response: str) -> Optional[tuple[list[str], str]]:
    try:
        obj = json.loads(response)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", response, re.DOTALL)
        if match:
            try:
                obj = json.loads(match.group())
            except (json.JSONDecodeError, ValueError):
                return None
        else:
            return None

    types = obj.get("analysis_types", [])
    explanation = obj.get("explanation", "Routing completed.")

    if not isinstance(types, list):
        return None

    valid = [t for t in types if t in ALLOWED_TYPES][:MAX_TYPES]
    if not valid:
        return None

    return valid, explanation


def _keyword_route(question: str) -> tuple[list[str], str]:
    q_lower = question.lower()
    matched = set()

    for keywords, analysis_type in KEYWORD_RULES:
        for kw in keywords:
            if kw in q_lower:
                matched.add(analysis_type)
                break

    ordered = [t for t in ["summary", "missing_outliers", "best_worst", "basic_chart"] if t in matched]

    if not ordered:
        ordered = ["summary"]

    ordered = ordered[:MAX_TYPES]

    if len(ordered) == 1:
        explanation = f"Chose {ordered[0]} based on keywords in your question."
    else:
        types_str = ", ".join(ordered)
        explanation = f"Chose {types_str} based on keywords in your question."

    return ordered, explanation
