from __future__ import annotations

from collections.abc import Generator
from typing import Protocol, runtime_checkable

from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


@runtime_checkable
class SessionManager(Protocol):
    """Provides SQLAlchemy sessions and engine access."""

    @property
    def engine(self) -> Engine: ...

    def create_session(self) -> Session: ...

    def provide_session(self) -> Generator[Session, None, None]: ...

    def check_connection(self) -> None: ...
