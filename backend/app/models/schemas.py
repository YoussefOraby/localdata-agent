from typing import Any, Literal, Optional

from pydantic import BaseModel


AnalysisType = Literal["summary", "missing_outliers", "best_worst", "basic_chart"]


class AnalyzeRequest(BaseModel):
    analysis_type: AnalysisType


class AnalyzeResponse(BaseModel):
    success: bool
    analysis_type: str
    file_name: Optional[str] = None
    rows: Optional[int] = None
    columns: Optional[int] = None
    column_names: Optional[list[str]] = None
    result: Optional[dict] = None
    explanation: Optional[str] = None
    chart: Optional[dict] = None
    generated_code: Optional[str] = None
    steps: list[str] = []
    error: Optional[str] = None
    execution_time_seconds: Optional[float] = None
