"""Compatibility shim — prefer ``app.patterns.events.observer_registry``."""

from app.patterns.events.observer_registry import EventHandlerRegistry

__all__ = ["EventHandlerRegistry"]
