import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)


class JSONLLogger:
    def __init__(self, log_dir: Optional[str] = None):
        raw_dir = log_dir or settings.LOG_DIR
        self.log_dir = self._resolve(raw_dir)
        os.makedirs(self.log_dir, exist_ok=True)
        self.log_path = os.path.join(self.log_dir, "agent_runs.jsonl")

    @staticmethod
    def _resolve(path: str) -> str:
        if os.path.isabs(path):
            return path
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        return os.path.join(project_root, path)

    def log_run(self, data: dict) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "template",
            "file_name": data.get("file_name"),
            "analysis_type": data.get("analysis_type"),
            "rows": data.get("rows"),
            "columns": data.get("columns"),
            "success": data.get("success", False),
            "error": data.get("error"),
            "execution_time_seconds": data.get("execution_time_seconds"),
            "tool_used": "python_sandbox",
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error("Failed to write log entry: %s", e)

    def log_agent_run(self, data: dict) -> None:
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "mode": "agent",
            "file_name": data.get("file_name"),
            "question": data.get("question"),
            "selected_analysis_types": data.get("selected_analysis_types"),
            "success": data.get("success", False),
            "error": data.get("error"),
            "execution_time_seconds": data.get("execution_time_seconds"),
            "tool_used": "langgraph_agent",
        }
        try:
            with open(self.log_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as e:
            logger.error("Failed to write log entry: %s", e)

    def get_recent_runs(self, limit: int = 10) -> list[dict]:
        if not os.path.exists(self.log_path):
            return []
        runs = []
        try:
            with open(self.log_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        runs.append(json.loads(line))
        except Exception as e:
            logger.error("Failed to read log file: %s", e)
        return runs[-limit:]
