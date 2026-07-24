"""Compatibility shim — prefer ``app.infrastructure.persistence.session``."""

from collections.abc import Generator

from sqlalchemy.orm import Session

from app.infrastructure.persistence.base import Base
from app.infrastructure.persistence.session import get_session_manager

__all__ = ["Base", "SessionLocal", "engine", "get_db", "check_database_connection"]

_manager = get_session_manager()
engine = _manager.engine
SessionLocal = _manager.create_session


def get_db() -> Generator[Session, None, None]:
    yield from get_session_manager().provide_session()


def check_database_connection() -> None:
    get_session_manager().check_connection()
