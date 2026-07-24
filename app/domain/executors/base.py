"""Compatibility shim — prefer ``app.patterns.executions.strategies``."""

from app.patterns.executions.strategies.base import BaseNodeExecutor

__all__ = ["BaseNodeExecutor"]
