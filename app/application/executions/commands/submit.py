"""Submit node outputs command."""

from __future__ import annotations

from typing import Any

from app.application.events.event_store import EventStore
from app.application.executions.graph_runtime import GraphRuntime
from app.application.executions.input_binder import GraphInputBinder
from app.application.executions.upstream_resolver import UpstreamInputResolver
from app.domain.enums import ExecutionStatus, NodeStatus, WorkflowStatus
from app.domain.events.payloads import NodeCompletedPayload, NodeStartedPayload
from app.domain.events.types import WorkflowEventType
from app.domain.exceptions import (
    InvalidTransitionError,
    NodeExecutionError,
    UpstreamNotReadyError,
    VersionConflictError,
)
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.ports.execution_context import ExecutionContext
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.domain.ports.projection_repository import ProjectionRepositoryPort as ProjectionRepository
from app.infrastructure.executions.projection_reader import PrefetchedNodeProjectionReader
from app.infrastructure.persistence.models import WorkflowNodeInstance
from app.patterns.executions.builders.seed_memento import SeedDefaultsMemento
from app.patterns.executions.factories import NodeExecutorRegistry


class SubmitNodeOutputsCommand:
    """Validates, executes a PENDING task node, and advances the workflow graph."""

    def __init__(
        self,
        *,
        definitions: DefinitionRepository,
        instances: InstanceRepository,
        projections: ProjectionRepository,
        events: EventStore,
        executors: NodeExecutorRegistry,
        runtime: GraphRuntime,
    ) -> None:
        self._definitions = definitions
        self._instances = instances
        self._projections = projections
        self._events = events
        self._executors = executors
        self._runtime = runtime

    def submit_node_outputs(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        outputs: dict[str, Any],
        executed_by: str | None = None,
        expected_revision: int | None = None,
    ) -> WorkflowNodeInstance:
        instance = self._instances.require_workflow_instance(workflow_instance_id)
        if instance.status != WorkflowStatus.RUNNING:
            raise InvalidTransitionError(
                f"Cannot submit node outputs while workflow is {instance.status.value}"
            )
        if expected_revision is not None and instance.current_revision != expected_revision:
            raise VersionConflictError(
                f"Workflow instance revision conflict: expected {expected_revision}, "
                f"got {instance.current_revision}"
            )

        graph = self._runtime.load_graph(instance)
        graph_node = graph.require_node(workflow_node_id)
        if not graph_node.is_task:
            raise NodeExecutionError(f"Node '{workflow_node_id}' is not a task node")

        node_instance = self._instances.require_node_instance_by_graph_id(
            workflow_instance_id, workflow_node_id
        )
        if node_instance.status != NodeStatus.PENDING:
            raise UpstreamNotReadyError(
                f"Node '{workflow_node_id}' is not ready for submission "
                f"(status={node_instance.status.value})"
            )

        node_version = self._definitions.get_node_definition_version_by_id(
            node_instance.node_definition_version_id
        )
        if node_version is None:
            raise NodeExecutionError("Pinned node definition version not found")

        definition_json = node_version.definition_json
        node_instances = self._instances.list_node_instances(workflow_instance_id)
        statuses_by_graph_id = {
            node.workflow_node_id: node.status for node in node_instances
        }
        input_binder = GraphInputBinder(
            UpstreamInputResolver(
                PrefetchedNodeProjectionReader(
                    values_by_graph_id=self._projections.get_node_values_map_for_instance(
                        workflow_instance_id
                    ),
                    statuses_by_graph_id=statuses_by_graph_id,
                )
            )
        )
        resolved_inputs = input_binder.resolve(
            workflow_instance_id=workflow_instance_id,
            graph_node=graph_node,
        )
        seed_memento = SeedDefaultsMemento.from_storage(instance.seed_defaults_json)
        executor = self._executors.for_definition(definition_json)
        context = ExecutionContext(
            workflow_instance_id=workflow_instance_id,
            workflow_node_instance_id=node_instance.id,
            workflow_node_id=workflow_node_id,
            node_definition_version_id=node_instance.node_definition_version_id,
            base_kind=executor.base_kind,
            definition_json=definition_json,
            resolved_inputs=resolved_inputs.values,
            locked_input_keys=resolved_inputs.locked_keys,
            execution_number=node_instance.current_execution + 1,
            seed_defaults=seed_memento.for_node(workflow_node_id),
        )

        self._instances.update_node_status(node_instance, NodeStatus.RUNNING)
        self._events.append(
            workflow_instance_id=workflow_instance_id,
            event_type=WorkflowEventType.NODE_STARTED.value,
            payload_json=NodeStartedPayload(
                workflow_instance_id=workflow_instance_id,
                workflow_node_instance_id=node_instance.id,
                workflow_node_id=workflow_node_id,
                execution_number=context.execution_number,
            ).to_dict(),
            created_by=executed_by,
        )

        final_outputs = executor.run(context, outputs)

        self._instances.create_node_execution(
            workflow_instance_id=workflow_instance_id,
            node_instance=node_instance,
            inputs_json=dict(resolved_inputs.values),
            outputs_json=final_outputs,
            status=ExecutionStatus.COMPLETED,
            executed_by=executed_by,
        )
        self._instances.update_node_status(node_instance, NodeStatus.COMPLETED)
        self._events.append(
            workflow_instance_id=workflow_instance_id,
            event_type=WorkflowEventType.NODE_COMPLETED.value,
            payload_json=NodeCompletedPayload(
                workflow_instance_id=workflow_instance_id,
                workflow_node_instance_id=node_instance.id,
                workflow_node_id=workflow_node_id,
                execution_number=node_instance.current_execution,
                outputs=final_outputs,
                cost_contribution=executor.cost_contribution(definition_json, final_outputs),
            ).to_dict(),
            created_by=executed_by,
        )

        self._runtime.advance(instance, graph)
        return node_instance
