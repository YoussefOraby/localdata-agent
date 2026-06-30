from dataclasses import dataclass, field
from typing import Optional


@dataclass
class AgentState:
    question: str
    file_bytes: bytes
    file_name: str
    selected_analysis_types: list[str] = field(default_factory=list)
    results: list[dict] = field(default_factory=list)
    final_answer: Optional[str] = None
    steps: list[str] = field(default_factory=list)
    error: Optional[str] = None
