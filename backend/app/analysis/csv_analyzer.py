import logging
import os
import traceback
from io import StringIO
from typing import Optional

import pandas as pd

from app.analysis.templates import get_template
from app.config import settings
from app.executor.sandbox import PythonSandbox
from app.llm.ollama_client import OllamaClient

logger = logging.getLogger(__name__)


class CSVAnalyzer:
    def __init__(self):
        self.sandbox = PythonSandbox(timeout=settings.MAX_EXECUTION_TIMEOUT)
        self.llm = OllamaClient()
        self.ollama_available = self.llm.is_available()

    def analyze(self, file_bytes: bytes, file_name: str, analysis_type: str) -> dict:
        steps = []

        if not file_bytes or not file_bytes.strip():
            return {
                "success": False,
                "analysis_type": analysis_type,
                "file_name": file_name,
                "rows": 0,
                "columns": 0,
                "column_names": [],
                "result": None,
                "explanation": "The uploaded file is empty.",
                "chart": None,
                "generated_code": None,
                "steps": [],
                "error": "Empty file.",
                "execution_time_seconds": None,
            }

        steps.append("Reading CSV file")
        try:
            decoded = file_bytes.decode("utf-8", errors="replace")
            df = pd.read_csv(StringIO(decoded))
            if df.columns.duplicated().any():
                df = df.loc[:, ~df.columns.duplicated()]
        except pd.errors.EmptyDataError:
            return {
                "success": False,
                "analysis_type": analysis_type,
                "file_name": file_name,
                "rows": 0,
                "columns": 0,
                "column_names": [],
                "result": None,
                "explanation": "The CSV file is empty.",
                "chart": None,
                "generated_code": None,
                "steps": steps,
                "error": "Empty CSV file.",
                "execution_time_seconds": None,
            }
        except pd.errors.ParserError as e:
            return {
                "success": False,
                "analysis_type": analysis_type,
                "file_name": file_name,
                "rows": 0,
                "columns": 0,
                "column_names": [],
                "result": None,
                "explanation": f"Could not parse CSV: {e}",
                "chart": None,
                "generated_code": None,
                "steps": steps,
                "error": f"CSV parse error: {e}",
                "execution_time_seconds": None,
            }
        except Exception as e:
            return {
                "success": False,
                "analysis_type": analysis_type,
                "file_name": file_name,
                "rows": None,
                "columns": None,
                "column_names": None,
                "result": None,
                "explanation": f"Failed to read CSV: {e}",
                "chart": None,
                "generated_code": None,
                "steps": steps,
                "error": f"CSV read error: {e}",
                "execution_time_seconds": None,
            }

        if df.empty:
            return {
                "success": False,
                "analysis_type": analysis_type,
                "file_name": file_name,
                "rows": 0,
                "columns": 0,
                "column_names": [],
                "result": None,
                "explanation": "The CSV file is empty.",
                "chart": None,
                "generated_code": None,
                "steps": steps,
                "error": "Empty CSV file.",
                "execution_time_seconds": None,
            }

        rows, cols = df.shape
        column_names = df.columns.tolist()

        steps.append(f"Loaded {rows} rows x {cols} columns")
        steps.append("Inspecting columns")

        code = get_template(analysis_type)
        if not code:
            return {
                "success": False,
                "analysis_type": analysis_type,
                "file_name": file_name,
                "rows": rows,
                "columns": cols,
                "column_names": column_names,
                "result": None,
                "explanation": f"Unknown analysis type: {analysis_type}",
                "chart": None,
                "generated_code": None,
                "steps": steps,
                "error": f"Unknown analysis type: {analysis_type}",
                "execution_time_seconds": None,
            }

        steps.append("Running Python analysis")
        sandbox_result = self.sandbox.execute(code, context={"df": df})

        if not sandbox_result.success:
            steps.append("Analysis failed")
            error_msg = sandbox_result.error or "Unknown sandbox error"
            return {
                "success": False,
                "analysis_type": analysis_type,
                "file_name": file_name,
                "rows": rows,
                "columns": cols,
                "column_names": column_names,
                "result": None,
                "explanation": f"Analysis failed: {error_msg[:500]}",
                "chart": None,
                "generated_code": code,
                "steps": steps,
                "error": error_msg[:1000],
                "execution_time_seconds": sandbox_result.execution_time_seconds,
            }

        steps.append("Preparing chart/result")
        result_data = sandbox_result.result if sandbox_result.result else {}
        if not isinstance(result_data, dict):
            result_data = {"raw": result_data}

        chart = result_data.get("chart") if isinstance(result_data, dict) else None

        explanation = self._generate_explanation(result_data, analysis_type, df)

        steps.append("Analysis completed")
        return {
            "success": True,
            "analysis_type": analysis_type,
            "file_name": file_name,
            "rows": rows,
            "columns": cols,
            "column_names": column_names,
            "result": result_data,
            "explanation": explanation,
            "chart": chart,
            "generated_code": code,
            "steps": steps,
            "error": None,
            "execution_time_seconds": sandbox_result.execution_time_seconds,
        }

    def _generate_explanation(self, result_data: dict, analysis_type: str, df: pd.DataFrame) -> str:
        if not result_data:
            return "Analysis completed but produced no results."

        if self.ollama_available:
            try:
                summary = result_data.get("summary", "")
                insights = result_data.get("insights", [])
                metrics = result_data.get("metrics", {})
                prompt = (
                    f"I analyzed a CSV dataset with {len(df)} rows and {len(df.columns)} columns "
                    f"(analysis type: {analysis_type}). "
                    f"Summary: {summary}. "
                    f"Metrics: {metrics}. "
                    f"Key insights: {'; '.join(insights[:5])}. "
                    f"Write a short paragraph explaining the most important findings in plain language."
                )
                explanation = self.llm.generate(prompt)
                if explanation and not explanation.startswith("Error"):
                    return explanation.strip()
            except Exception:
                logger.debug("LLM explanation failed, using fallback")

        return self._fallback_explanation(result_data, analysis_type)

    def _fallback_explanation(self, result_data: dict, analysis_type: str) -> str:
        summary = result_data.get("summary", "")
        insights = result_data.get("insights", [])
        if insights:
            return summary + "\n\nKey findings:\n- " + "\n- ".join(insights[:5])
        return summary or f"{analysis_type.replace('_', ' ').title()} analysis completed."
