"""Deprecated shim — use ``ExecutionService`` / commands / queries instead."""

from app.application.executions.service import ExecutionService as WorkflowOrchestrator

__all__ = ["WorkflowOrchestrator"]
