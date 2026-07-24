"""Port: append-only workflow event persistence."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class EventRepositoryPort(Protocol):
    def get_next_sequence_number(self, workflow_instance_id: str) -> int: ...

    def append_event(
        self,
        *,
        workflow_instance_id: str,
        event_type: str,
        payload_json: dict,
        created_by: str | None = None,
        previous_hash: str | None = None,
        current_hash: str | None = None,
        sequence_number: int | None = None,
    ) -> Any: ...

    def get_latest_event(self, workflow_instance_id: str) -> Any | None: ...

    def list_events(
        self, workflow_instance_id: str, *, after_sequence: int | None = None
    ) -> list[Any]: ...

    def list_events_page(
        self,
        workflow_instance_id: str,
        page: Any,
        *,
        after_sequence: int | None = None,
        event_type: str | None = None,
    ) -> Any: ...

    def list_all_events(self) -> list[Any]: ...
