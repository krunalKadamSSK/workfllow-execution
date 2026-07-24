"""Compatibility shim — prefer ``app.patterns.executions.builders``."""

from app.patterns.executions.builders.instance_builder import WorkflowInstanceBuilder

__all__ = ["WorkflowInstanceBuilder"]
