"""Compatibility shim — prefer ``event_handler``."""

from app.domain.ports.event_handler import EventHandler

__all__ = ["EventHandler"]
