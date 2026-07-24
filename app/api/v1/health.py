"""Shim — use ``app.api.routes.v1.health``."""

from app.api.routes.v1.health import router

__all__ = ["router"]
