"""Shim package — use ``app.infrastructure.persistence``."""

from app.infrastructure.persistence import (
    Base,
    SqlAlchemySessionManager,
    get_session_manager,
    reset_session_manager,
)

__all__ = [
    "Base",
    "SqlAlchemySessionManager",
    "get_session_manager",
    "reset_session_manager",
]
