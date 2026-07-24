"""Start-workflow command."""

from __future__ import annotations

from typing import Any

from app.application.events.event_store import EventStore
from app.application.executions.graph_runtime import GraphRuntime
from app.domain.events.payloads import WorkflowStartedPayload
from app.domain.events.types import WorkflowEventType
from app.domain.metadata import InstanceMetadata
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.infrastructure.persistence.models import WorkflowInstance
from app.patterns.executions.builders.instance_builder import WorkflowInstanceBuilder
from app.patterns.executions.builders.seed_memento import (
    SeedDefaultsMementoBuilder,
    require_seed_source_compatible,
)


class StartWorkflowCommand:
    """Creates a workflow instance, emits WORKFLOW_STARTED, and advances the graph."""

    def __init__(
        self,
        *,
        definitions: DefinitionRepository,
        instances: InstanceRepository,
        events: EventStore,
        runtime: GraphRuntime,
    ) -> None:
        self._definitions = definitions
        self._instances = instances
        self._events = events
        self._runtime = runtime
        self._builder = WorkflowInstanceBuilder(
            definition_repository=definitions,
            instance_repository=instances,
        )

    def start_workflow(
        self,
        *,
        name: str,
        workflow_definition_id: str,
        version: int | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | InstanceMetadata | None = None,
        seed_from_instance_id: str | None = None,
    ) -> WorkflowInstance:
        meta = (
            metadata
            if isinstance(metadata, InstanceMetadata)
            else InstanceMetadata.from_storage(metadata)
        )
        seed_defaults: dict[str, Any] = {}
        if seed_from_instance_id:
            source = self._instances.require_workflow_instance(seed_from_instance_id)
            require_seed_source_compatible(
                source=source,
                target_workflow_definition_id=workflow_definition_id,
            )
            memento = SeedDefaultsMementoBuilder(
                instance_repository=self._instances,
                definition_repository=self._definitions,
            ).build(seed_from_instance_id)
            seed_defaults = memento.to_storage()

        built = self._builder.build(
            name=name,
            workflow_definition_id=workflow_definition_id,
            version=version,
            created_by=created_by,
            metadata=meta,
            seed_defaults=seed_defaults,
        )
        snapshot_json = dict(built.workflow_version.definition_json)

        self._events.append(
            workflow_instance_id=built.instance.id,
            event_type=WorkflowEventType.WORKFLOW_STARTED.value,
            payload_json=WorkflowStartedPayload(
                workflow_instance_id=built.instance.id,
                workflow_definition_id=workflow_definition_id,
                workflow_definition_version_id=built.workflow_version.id,
                snapshot_json=snapshot_json,
            ).to_dict(),
            created_by=created_by,
        )

        self._runtime.transition_to_running(built.instance)
        self._runtime.advance(built.instance, built.graph)
        return built.instance
