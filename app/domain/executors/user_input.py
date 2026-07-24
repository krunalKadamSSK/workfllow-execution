"""Compatibility shim — prefer ``app.patterns.executions.strategies``."""

from app.patterns.executions.strategies.user_input import UserInputExecutor

__all__ = ["UserInputExecutor"]
