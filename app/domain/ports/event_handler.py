"""Port: observer that reacts to appended workflow events."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.domain.events.stored_event import StoredEvent


@runtime_checkable
class EventHandler(Protocol):
    def handles(self) -> frozenset[str]: ...

    def handle(self, event: StoredEvent) -> None: ...
