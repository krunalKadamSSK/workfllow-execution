"""Compatibility shim — prefer ``app.patterns.executions.strategies``."""

from app.patterns.executions.strategies.template import substitute_templates

__all__ = ["substitute_templates"]
