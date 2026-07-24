from __future__ import annotations

from typing import Protocol, runtime_checkable

from sqlalchemy.orm import Session


@runtime_checkable
class Repository(Protocol):
    """Marker interface for persistence repositories."""

    @property
    def session(self) -> Session: ...
