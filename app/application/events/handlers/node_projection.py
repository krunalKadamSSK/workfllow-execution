from __future__ import annotations

from app.domain.events.stored_event import StoredEvent
from app.domain.events.types import WorkflowEventType
from app.infrastructure.db.repositories.projections import ProjectionRepository


class WorkflowNodeProjectionHandler:
    """Materializes per-node output values when nodes complete."""

    def __init__(self, projection_repository: ProjectionRepository) -> None:
        self._projections = projection_repository

    def handles(self) -> frozenset[str]:
        return frozenset({WorkflowEventType.NODE_COMPLETED.value})

    def handle(self, event: StoredEvent) -> None:
        payload = event.payload_json
        self._projections.upsert_node_projection(
            workflow_instance_id=event.workflow_instance_id,
            workflow_node_instance_id=payload["workflow_node_instance_id"],
            current_values_json=dict(payload.get("outputs", {})),
        )
