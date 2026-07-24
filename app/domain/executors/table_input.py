"""Compatibility shim — prefer ``app.patterns.executions.strategies``."""

from app.patterns.executions.strategies.table_input import TableExecutor

__all__ = ["TableExecutor"]
