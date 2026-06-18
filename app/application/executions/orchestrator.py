from __future__ import annotations

from typing import Any

from app.application.events.event_store import EventStore
from app.application.executions.input_binder import GraphInputBinder
from app.application.executions.instance_builder import WorkflowInstanceBuilder
from app.application.executions.scheduler import GraphScheduler
from app.application.executions.upstream_resolver import UpstreamInputResolver
from app.domain.enums import ExecutionStatus, NodeStatus, WorkflowStatus
from app.domain.events.payloads import (
    NodeCompletedPayload,
    NodeInvalidatedPayload,
    NodeReadyPayload,
    NodeStartedPayload,
    WorkflowStartedPayload,
    WorkflowStatusChangedPayload,
)
from app.domain.events.types import WorkflowEventType
from app.domain.exceptions import (
    InvalidTransitionError,
    NodeExecutionError,
    UpstreamNotReadyError,
    VersionConflictError,
)
from app.domain.executors.registry import NodeExecutorRegistry
from app.domain.graph.workflow_graph import WorkflowGraph
from app.domain.ports.executors import ExecutionContext
from app.domain.state.workflow import WorkflowStateMachine
from app.infrastructure.db.models import WorkflowInstance, WorkflowNodeInstance
from app.infrastructure.db.repositories.definitions import DefinitionRepository
from app.infrastructure.db.repositories.instances import InstanceRepository
from app.infrastructure.db.repositories.projections import ProjectionRepository
from app.infrastructure.executions.projection_reader import DbNodeProjectionReader


class WorkflowOrchestrator:
    """Mediator coordinating workflow lifecycle, node execution, and event emission."""

    def __init__(
        self,
        *,
        definition_repository: DefinitionRepository,
        instance_repository: InstanceRepository,
        projection_repository: ProjectionRepository,
        event_store: EventStore,
        executor_registry: NodeExecutorRegistry,
    ) -> None:
        self._definitions = definition_repository
        self._instances = instance_repository
        self._projections = projection_repository
        self._events = event_store
        self._executors = executor_registry
        self._workflow_sm = WorkflowStateMachine()
        self._builder = WorkflowInstanceBuilder(
            definition_repository=definition_repository,
            instance_repository=instance_repository,
        )
        self._input_binder = GraphInputBinder(
            UpstreamInputResolver(DbNodeProjectionReader(projection_repository))
        )

    def start_workflow(
        self,
        *,
        name: str,
        workflow_definition_id: str,
        version: int | None = None,
        created_by: str | None = None,
    ) -> WorkflowInstance:
        built = self._builder.build(
            name=name,
            workflow_definition_id=workflow_definition_id,
            version=version,
            created_by=created_by,
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

        self._workflow_sm.transition(built.instance.status, WorkflowStatus.RUNNING)
        self._instances.update_workflow_status(built.instance, WorkflowStatus.RUNNING)
        self._advance(built.instance, built.graph)
        return built.instance

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

        graph = self._load_graph(instance)
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
        resolved_inputs = self._input_binder.resolve(
            workflow_instance_id=workflow_instance_id,
            graph_node=graph_node,
        )
        executor = self._executors.get(definition_json["baseKind"])
        context = ExecutionContext(
            workflow_instance_id=workflow_instance_id,
            workflow_node_instance_id=node_instance.id,
            workflow_node_id=workflow_node_id,
            node_definition_version_id=node_instance.node_definition_version_id,
            base_kind=definition_json["baseKind"],
            definition_json=definition_json,
            resolved_inputs=resolved_inputs.values,
            locked_input_keys=resolved_inputs.locked_keys,
            execution_number=node_instance.current_execution + 1,
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
            ).to_dict(),
            created_by=executed_by,
        )

        self._advance(instance, graph)
        return node_instance

    def pause_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        return self._change_workflow_status(
            workflow_instance_id,
            target=WorkflowStatus.PAUSED,
            event_type=WorkflowEventType.WORKFLOW_PAUSED,
            expected_revision=expected_revision,
        )

    def resume_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        instance = self._change_workflow_status(
            workflow_instance_id,
            target=WorkflowStatus.RUNNING,
            event_type=WorkflowEventType.WORKFLOW_RESUMED,
            expected_revision=expected_revision,
        )
        self._advance(instance, self._load_graph(instance))
        return instance

    def cancel_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        return self._change_workflow_status(
            workflow_instance_id,
            target=WorkflowStatus.CANCELLED,
            event_type=WorkflowEventType.WORKFLOW_CANCELLED,
            expected_revision=expected_revision,
        )

    def get_instance_state(self, workflow_instance_id: str) -> dict[str, Any]:
        instance = self._instances.require_workflow_instance(workflow_instance_id)
        node_instances = self._instances.list_node_instances(workflow_instance_id)
        workflow_state = self._projections.get_workflow_state(workflow_instance_id)
        graph = self._load_graph(instance)
        return {
            "instance": instance,
            "node_instances": node_instances,
            "workflow_projection": workflow_state,
            "pending_node_forms": self._prepare_pending_node_forms(
                workflow_instance_id, node_instances, graph
            ),
        }

    def _prepare_pending_node_forms(
        self,
        workflow_instance_id: str,
        node_instances: list[WorkflowNodeInstance],
        graph: WorkflowGraph,
    ) -> dict[str, dict[str, Any]]:
        pending_forms: dict[str, dict[str, Any]] = {}

        for node_instance in node_instances:
            if node_instance.status != NodeStatus.PENDING:
                continue

            graph_node = graph.require_node(node_instance.workflow_node_id)
            node_version = self._definitions.get_node_definition_version_by_id(
                node_instance.node_definition_version_id
            )
            if node_version is None:
                continue

            definition_json = node_version.definition_json
            resolved_inputs = self._input_binder.resolve(
                workflow_instance_id=workflow_instance_id,
                graph_node=graph_node,
            )
            executor = self._executors.get(definition_json["baseKind"])
            context = ExecutionContext(
                workflow_instance_id=workflow_instance_id,
                workflow_node_instance_id=node_instance.id,
                workflow_node_id=node_instance.workflow_node_id,
                node_definition_version_id=node_instance.node_definition_version_id,
                base_kind=definition_json["baseKind"],
                definition_json=definition_json,
                resolved_inputs=resolved_inputs.values,
                locked_input_keys=resolved_inputs.locked_keys,
                execution_number=node_instance.current_execution,
            )
            pending_forms[node_instance.workflow_node_id] = {
                "fields": executor.prepare_form_fields(context),
            }

        return pending_forms

    def _change_workflow_status(
        self,
        workflow_instance_id: str,
        *,
        target: WorkflowStatus,
        event_type: WorkflowEventType,
        expected_revision: int | None,
    ) -> WorkflowInstance:
        instance = self._instances.require_workflow_instance(workflow_instance_id)
        previous = instance.status
        self._workflow_sm.transition(previous, target)
        self._instances.update_workflow_status(
            instance, target, expected_revision=expected_revision
        )
        self._events.append(
            workflow_instance_id=workflow_instance_id,
            event_type=event_type.value,
            payload_json=WorkflowStatusChangedPayload(
                workflow_instance_id=workflow_instance_id,
                from_status=previous.value,
                to_status=target.value,
            ).to_dict(),
        )
        return instance

    def _advance(self, instance: WorkflowInstance, graph: WorkflowGraph) -> None:
        if instance.status != WorkflowStatus.RUNNING:
            return

        scheduler = GraphScheduler(graph)
        node_instances = {
            node.workflow_node_id: node
            for node in self._instances.list_node_instances(instance.id)
        }
        statuses = {
            node_id: node.status for node_id, node in node_instances.items()
        }

        for graph_node in scheduler.ready_task_nodes(statuses):
            node_instance = node_instances[graph_node.id]
            if node_instance.status == NodeStatus.INVALIDATED:
                self._instances.update_node_status(node_instance, NodeStatus.PENDING)
            elif node_instance.status == NodeStatus.WAITING:
                self._instances.update_node_status(node_instance, NodeStatus.PENDING)
            else:
                continue

            self._events.append(
                workflow_instance_id=instance.id,
                event_type=WorkflowEventType.NODE_READY.value,
                payload_json=NodeReadyPayload(
                    workflow_instance_id=instance.id,
                    workflow_node_instance_id=node_instance.id,
                    workflow_node_id=graph_node.id,
                    node_definition_version_id=node_instance.node_definition_version_id,
                ).to_dict(),
            )

        statuses = {
            node.workflow_node_id: node.status
            for node in self._instances.list_node_instances(instance.id)
        }
        if scheduler.all_tasks_completed(statuses):
            self._workflow_sm.transition(instance.status, WorkflowStatus.COMPLETED)
            self._instances.update_workflow_status(instance, WorkflowStatus.COMPLETED)
            self._events.append(
                workflow_instance_id=instance.id,
                event_type=WorkflowEventType.WORKFLOW_COMPLETED.value,
                payload_json=WorkflowStatusChangedPayload(
                    workflow_instance_id=instance.id,
                    from_status=WorkflowStatus.RUNNING.value,
                    to_status=WorkflowStatus.COMPLETED.value,
                ).to_dict(),
            )

    def invalidate_downstream(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        reason: str,
    ) -> list[WorkflowNodeInstance]:
        instance = self._instances.require_workflow_instance(workflow_instance_id)
        graph = self._load_graph(instance)
        scheduler = GraphScheduler(graph)
        invalidated: list[WorkflowNodeInstance] = []

        for graph_node in scheduler.downstream_task_nodes(workflow_node_id):
            node_instance = self._instances.get_node_instance_by_graph_id(
                workflow_instance_id, graph_node.id
            )
            if node_instance is None:
                continue
            if node_instance.status not in {
                NodeStatus.PENDING,
                NodeStatus.RUNNING,
                NodeStatus.COMPLETED,
            }:
                continue

            self._instances.update_node_status(node_instance, NodeStatus.INVALIDATED)
            self._events.append(
                workflow_instance_id=workflow_instance_id,
                event_type=WorkflowEventType.NODE_INVALIDATED.value,
                payload_json=NodeInvalidatedPayload(
                    workflow_instance_id=workflow_instance_id,
                    workflow_node_instance_id=node_instance.id,
                    workflow_node_id=graph_node.id,
                    reason=reason,
                    upstream_node_id=workflow_node_id,
                ).to_dict(),
            )
            invalidated.append(node_instance)

        if instance.status == WorkflowStatus.COMPLETED:
            self._workflow_sm.transition(instance.status, WorkflowStatus.RUNNING)
            self._instances.update_workflow_status(instance, WorkflowStatus.RUNNING)

        if invalidated:
            self._advance(instance, graph)

        return invalidated

    def _load_graph(self, instance: WorkflowInstance) -> WorkflowGraph:
        snapshot = self._instances.get_snapshot(instance.id)
        if snapshot is not None:
            return WorkflowGraph.from_definition_json(snapshot.snapshot_json)

        version = self._definitions.get_workflow_definition_version_by_id(
            instance.workflow_definition_version_id
        )
        if version is None:
            raise NodeExecutionError("Workflow definition version not found for instance")
        return WorkflowGraph.from_definition_json(version.definition_json)
