from __future__ import annotations

from app.application.events.handlers.workflow_state import (
    apply_workflow_projection_event,
    initial_workflow_state,
)
from app.domain.events.stored_event import StoredEvent
from app.domain.events.types import WorkflowEventType
from app.infrastructure.db.repositories.projections import ProjectionRepository


class WorkflowProjectionHandler:
    """Maintains workflow-level read model from the event stream."""

    _HANDLED = frozenset(
        {
            WorkflowEventType.WORKFLOW_STARTED.value,
            WorkflowEventType.WORKFLOW_PAUSED.value,
            WorkflowEventType.WORKFLOW_RESUMED.value,
            WorkflowEventType.WORKFLOW_COMPLETED.value,
            WorkflowEventType.WORKFLOW_CANCELLED.value,
            WorkflowEventType.NODE_READY.value,
            WorkflowEventType.NODE_STARTED.value,
            WorkflowEventType.NODE_COMPLETED.value,
            WorkflowEventType.NODE_FAILED.value,
            WorkflowEventType.NODE_INVALIDATED.value,
        }
    )

    def __init__(self, projection_repository: ProjectionRepository) -> None:
        self._projections = projection_repository

    def handles(self) -> frozenset[str]:
        return self._HANDLED

    def handle(self, event: StoredEvent) -> None:
        current = self._projections.get_workflow_state(event.workflow_instance_id)
        state = current if current is not None else initial_workflow_state()
        updated = apply_workflow_projection_event(state, event)
        self._projections.upsert_workflow_projection(
            workflow_instance_id=event.workflow_instance_id,
            current_state_json=updated,
        )
