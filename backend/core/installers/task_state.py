"""Shared state helpers for installation tasks and log accumulation."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

# Runtime storage for background installation tasks.
# Modules across the API and installer implementations import this structure
# to ensure every component references the same in-memory state.
installation_tasks: Dict[str, Dict[str, Any]] = {}


def create_task(installation_id: str, base_info: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize a new installation task with shared bookkeeping fields."""
    task = dict(base_info)
    task.setdefault("logs", [])
    task.setdefault("last_log", None)
    task.setdefault("last_log_at", None)
    task.setdefault("last_log_level", None)
    task.setdefault("logs_version", 0)
    installation_tasks[installation_id] = task
    return task


def get_task(installation_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve installation task data when available."""
    return installation_tasks.get(installation_id)


def append_installation_log(installation_id: str, log_entry: Dict[str, Any]) -> None:
    """Persist a log entry so polling clients can replay full history."""
    task = installation_tasks.get(installation_id)
    if task is None:
        return

    logs: List[Dict[str, Any]] = task.setdefault("logs", [])
    logs.append(log_entry)

    task["last_log"] = log_entry.get("message")
    task["last_log_at"] = log_entry.get("timestamp", datetime.now().isoformat())
    task["last_log_level"] = log_entry.get("level")
    task["logs_version"] = task.get("logs_version", 0) + 1


__all__ = [
    "installation_tasks",
    "create_task",
    "get_task",
    "append_installation_log",
]
