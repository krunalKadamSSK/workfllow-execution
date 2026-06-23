from __future__ import annotations

from typing import Any

from app.application.events.registry import EventHandlerRegistry
from app.domain.events.hash_chain import compute_event_hash
from app.domain.events.stored_event import StoredEvent
from app.infrastructure.db.repositories.events import EventRepository


class EventStore:
    """Append-only event store with optional hash chain and handler dispatch."""

    def __init__(
        self,
        event_repository: EventRepository,
        handler_registry: EventHandlerRegistry,
        *,
        hash_chain_enabled: bool = False,
    ) -> None:
        self._events = event_repository
        self._registry = handler_registry
        self._hash_chain_enabled = hash_chain_enabled

    def append(
        self,
        *,
        workflow_instance_id: str,
        event_type: str,
        payload_json: dict[str, Any],
        created_by: str | None = None,
    ) -> StoredEvent:
        sequence_number = self._events.get_next_sequence_number(workflow_instance_id)
        previous_hash: str | None = None
        current_hash: str | None = None

        if self._hash_chain_enabled:
            latest = self._events.get_latest_event(workflow_instance_id)
            previous_hash = latest.current_hash if latest is not None else None
            current_hash = compute_event_hash(
                previous_hash=previous_hash,
                sequence_number=sequence_number,
                event_type=event_type,
                payload_json=payload_json,
            )

        event = self._events.append_event(
            workflow_instance_id=workflow_instance_id,
            event_type=event_type,
            payload_json=payload_json,
            created_by=created_by,
            previous_hash=previous_hash,
            current_hash=current_hash,
            sequence_number=sequence_number,
        )
        stored = StoredEvent.from_model(event)
        self._registry.dispatch(stored)
        return stored

    def list_events(
        self, workflow_instance_id: str, *, after_sequence: int | None = None
    ) -> list[StoredEvent]:
        return [
            StoredEvent.from_model(event)
            for event in self._events.list_events(
                workflow_instance_id, after_sequence=after_sequence
            )
        ]

    def list_workflow_events(
        self, workflow_instance_id: str, *, after_sequence: int | None = None
    ):
        return self._events.list_events(
            workflow_instance_id, after_sequence=after_sequence
        )

    def list_all_workflow_events(self):
        return self._events.list_all_events()
