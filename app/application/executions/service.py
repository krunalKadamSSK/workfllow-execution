from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.application.events.event_store import EventStore
from app.application.events.factory import create_default_event_handler_registry
from app.application.executions.orchestrator import WorkflowOrchestrator
from app.core.config import settings
from app.domain.executors.registry import create_default_registry
from app.infrastructure.db.models import WorkflowInstance, WorkflowNodeInstance
from app.infrastructure.db.repositories.definitions import DefinitionRepository
from app.infrastructure.db.repositories.events import EventRepository
from app.infrastructure.db.repositories.instances import InstanceRepository
from app.infrastructure.db.repositories.projections import ProjectionRepository


class ExecutionService:
    """Facade for workflow execution use cases."""

    def __init__(
        self,
        orchestrator: WorkflowOrchestrator,
        event_store: EventStore,
        event_repository: EventRepository,
    ) -> None:
        self._orchestrator = orchestrator
        self._events = event_store
        self._event_repository = event_repository

    @classmethod
    def from_session(cls, session: Session) -> ExecutionService:
        definitions = DefinitionRepository(session)
        instances = InstanceRepository(session)
        events = EventRepository(session)
        projections = ProjectionRepository(session)
        handler_registry = create_default_event_handler_registry(
            projection_repository=projections,
            instance_repository=instances,
        )
        event_store = EventStore(
            events,
            handler_registry,
            hash_chain_enabled=settings.EVENT_HASH_CHAIN,
        )
        orchestrator = WorkflowOrchestrator(
            definition_repository=definitions,
            instance_repository=instances,
            projection_repository=projections,
            event_store=event_store,
            executor_registry=create_default_registry(),
        )
        return cls(orchestrator, event_store, events)

    def start_workflow(
        self,
        *,
        name: str,
        workflow_definition_id: str,
        version: int | None = None,
        created_by: str | None = None,
    ) -> WorkflowInstance:
        return self._orchestrator.start_workflow(
            name=name,
            workflow_definition_id=workflow_definition_id,
            version=version,
            created_by=created_by,
        )

    def submit_node_outputs(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        outputs: dict[str, Any],
        executed_by: str | None = None,
        expected_revision: int | None = None,
    ) -> WorkflowNodeInstance:
        return self._orchestrator.submit_node_outputs(
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=workflow_node_id,
            outputs=outputs,
            executed_by=executed_by,
            expected_revision=expected_revision,
        )

    def pause_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        return self._orchestrator.pause_workflow(
            workflow_instance_id, expected_revision=expected_revision
        )

    def resume_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        return self._orchestrator.resume_workflow(
            workflow_instance_id, expected_revision=expected_revision
        )

    def cancel_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        return self._orchestrator.cancel_workflow(
            workflow_instance_id, expected_revision=expected_revision
        )

    def get_instance_state(self, workflow_instance_id: str) -> dict[str, Any]:
        return self._orchestrator.get_instance_state(workflow_instance_id)

    def list_events(self, workflow_instance_id: str):
        return self._event_repository.list_events(workflow_instance_id)

    def invalidate_downstream(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        reason: str,
    ) -> list[WorkflowNodeInstance]:
        return self._orchestrator.invalidate_downstream(
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=workflow_node_id,
            reason=reason,
        )
