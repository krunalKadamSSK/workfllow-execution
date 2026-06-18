from __future__ import annotations

from app.domain.events.stored_event import StoredEvent
from app.domain.events.types import WorkflowEventType
from app.infrastructure.db.repositories.instances import InstanceRepository


class WorkflowSnapshotHandler:
    """Creates a workflow snapshot memento on WORKFLOW_STARTED."""

    def __init__(self, instance_repository: InstanceRepository) -> None:
        self._instances = instance_repository

    def handles(self) -> frozenset[str]:
        return frozenset({WorkflowEventType.WORKFLOW_STARTED.value})

    def handle(self, event: StoredEvent) -> None:
        snapshot_json = event.payload_json.get("snapshot_json")
        if not snapshot_json:
            return

        if self._instances.get_snapshot(event.workflow_instance_id) is not None:
            return

        self._instances.create_snapshot(
            workflow_instance_id=event.workflow_instance_id,
            snapshot_json=dict(snapshot_json),
        )
