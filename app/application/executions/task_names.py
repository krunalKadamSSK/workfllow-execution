"""Compatibility shim — prefer ``app.patterns.executions.helpers``."""

from app.patterns.executions.helpers.task_names import build_task_names, resolve_task_name

__all__ = ["build_task_names", "resolve_task_name"]
