"""Auto-complete task nodes whose strategy opts into ``runs_automatically()``."""

from __future__ import annotations

from typing import Any

from app.application.events.event_store import EventStore
from app.application.executions.input_binder import GraphInputBinder
from app.application.executions.upstream_resolver import UpstreamInputResolver
from app.domain.enums import ExecutionStatus, NodeStatus
from app.domain.events.payloads import NodeCompletedPayload, NodeStartedPayload
from app.domain.events.types import WorkflowEventType
from app.domain.exceptions import NodeExecutionError
from app.domain.graph.workflow_graph import GraphNode, WorkflowGraph
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.ports.execution_context import ExecutionContext
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.domain.ports.projection_repository import ProjectionRepositoryPort as ProjectionRepository
from app.infrastructure.executions.projection_reader import PrefetchedNodeProjectionReader
from app.infrastructure.persistence.models import WorkflowInstance, WorkflowNodeInstance
from app.patterns.executions.builders.seed_memento import SeedDefaultsMemento
from app.patterns.executions.factories import NodeExecutorRegistry


class AutoNodeRunner:
    """Runs automatic task strategies immediately after they become PENDING."""

    def __init__(
        self,
        *,
        definitions: DefinitionRepository,
        instances: InstanceRepository,
        projections: ProjectionRepository,
        events: EventStore,
        executors: NodeExecutorRegistry,
    ) -> None:
        self._definitions = definitions
        self._instances = instances
        self._projections = projections
        self._events = events
        self._executors = executors

    def try_complete(
        self,
        *,
        instance: WorkflowInstance,
        graph: WorkflowGraph,
        graph_node: GraphNode,
        node_instance: WorkflowNodeInstance,
    ) -> bool:
        """Execute the node when its strategy is automatic. Returns True if completed."""
        del graph  # Reserved for future binding that needs the full graph.
        node_version = self._definitions.get_node_definition_version_by_id(
            node_instance.node_definition_version_id
        )
        if node_version is None:
            raise NodeExecutionError("Pinned node definition version not found")

        definition_json = node_version.definition_json
        executor = self._executors.for_definition(definition_json)
        if not executor.runs_automatically():
            return False

        node_instances = self._instances.list_node_instances(instance.id)
        statuses_by_graph_id = {
            node.workflow_node_id: node.status for node in node_instances
        }
        input_binder = GraphInputBinder(
            UpstreamInputResolver(
                PrefetchedNodeProjectionReader(
                    values_by_graph_id=self._projections.get_node_values_map_for_instance(
                        instance.id
                    ),
                    statuses_by_graph_id=statuses_by_graph_id,
                )
            )
        )
        resolved_inputs = input_binder.resolve(
            workflow_instance_id=instance.id,
            graph_node=graph_node,
        )
        seed_memento = SeedDefaultsMemento.from_storage(instance.seed_defaults_json)
        context = ExecutionContext(
            workflow_instance_id=instance.id,
            workflow_node_instance_id=node_instance.id,
            workflow_node_id=graph_node.id,
            node_definition_version_id=node_instance.node_definition_version_id,
            base_kind=executor.base_kind,
            definition_json=definition_json,
            resolved_inputs=resolved_inputs.values,
            locked_input_keys=resolved_inputs.locked_keys,
            execution_number=node_instance.current_execution + 1,
            seed_defaults=seed_memento.for_node(graph_node.id),
        )

        self._instances.update_node_status(node_instance, NodeStatus.RUNNING)
        self._events.append(
            workflow_instance_id=instance.id,
            event_type=WorkflowEventType.NODE_STARTED.value,
            payload_json=NodeStartedPayload(
                workflow_instance_id=instance.id,
                workflow_node_instance_id=node_instance.id,
                workflow_node_id=graph_node.id,
                execution_number=context.execution_number,
            ).to_dict(),
        )

        outputs: dict[str, Any] = executor.on_ready(context)
        final_outputs = executor.run(context, outputs)

        self._instances.create_node_execution(
            workflow_instance_id=instance.id,
            node_instance=node_instance,
            inputs_json=dict(resolved_inputs.values),
            outputs_json=final_outputs,
            status=ExecutionStatus.COMPLETED,
        )
        self._instances.update_node_status(node_instance, NodeStatus.COMPLETED)
        self._events.append(
            workflow_instance_id=instance.id,
            event_type=WorkflowEventType.NODE_COMPLETED.value,
            payload_json=NodeCompletedPayload(
                workflow_instance_id=instance.id,
                workflow_node_instance_id=node_instance.id,
                workflow_node_id=graph_node.id,
                execution_number=node_instance.current_execution,
                outputs=final_outputs,
                cost_contribution=executor.cost_contribution(definition_json, final_outputs),
            ).to_dict(),
        )
        return True
