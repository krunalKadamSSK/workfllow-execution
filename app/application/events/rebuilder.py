from __future__ import annotations

from app.application.events.registry import EventHandlerRegistry
from app.domain.events.stored_event import StoredEvent
from app.infrastructure.db.repositories.events import EventRepository
from app.infrastructure.db.repositories.projections import ProjectionRepository


class ProjectionRebuilder:
    """Rebuilds read models by replaying the append-only event log."""

    def __init__(
        self,
        *,
        event_repository: EventRepository,
        projection_repository: ProjectionRepository,
        handler_registry: EventHandlerRegistry,
    ) -> None:
        self._events = event_repository
        self._projections = projection_repository
        self._registry = handler_registry

    def rebuild(self, workflow_instance_id: str) -> int:
        self._projections.delete_projections_for_instance(workflow_instance_id)
        events = self._events.list_events(workflow_instance_id)
        for event in events:
            self._registry.dispatch(StoredEvent.from_model(event))
        return len(events)
