"""Compatibility shim — prefer ``app.patterns.executions.helpers``."""

from app.patterns.executions.helpers.summary import build_execution_summary

__all__ = ["build_execution_summary"]
