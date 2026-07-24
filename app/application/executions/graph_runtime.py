"""Shared graph advancement / status / invalidate helpers for execution commands."""

from __future__ import annotations

from app.application.events.event_store import EventStore
from app.application.executions.auto_node_runner import AutoNodeRunner
from app.application.executions.scheduler import GraphScheduler
from app.domain.enums import NodeStatus, WorkflowStatus
from app.domain.events.payloads import (
    NodeInvalidatedPayload,
    NodeReadyPayload,
    WorkflowStatusChangedPayload,
)
from app.domain.events.types import WorkflowEventType
from app.domain.exceptions import NodeExecutionError
from app.domain.graph.workflow_graph import WorkflowGraph
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.domain.state.workflow import WorkflowStateMachine
from app.infrastructure.persistence.models import WorkflowInstance, WorkflowNodeInstance

_MAX_AUTO_ADVANCE_DEPTH = 64


class GraphRuntime:
    """Collaborator for load-graph, advance, status changes, and downstream invalidation."""

    def __init__(
        self,
        *,
        definition_repository: DefinitionRepository,
        instance_repository: InstanceRepository,
        event_store: EventStore,
        auto_runner: AutoNodeRunner | None = None,
    ) -> None:
        self._definitions = definition_repository
        self._instances = instance_repository
        self._events = event_store
        self._auto_runner = auto_runner
        self._workflow_sm = WorkflowStateMachine()

    def load_graph(self, instance: WorkflowInstance) -> WorkflowGraph:
        snapshot = self._instances.get_snapshot(instance.id)
        if snapshot is not None:
            return WorkflowGraph.from_definition_json(snapshot.snapshot_json)

        version = self._definitions.get_workflow_definition_version_by_id(
            instance.workflow_definition_version_id
        )
        if version is None:
            raise NodeExecutionError("Workflow definition version not found for instance")
        return WorkflowGraph.from_definition_json(version.definition_json)

    def change_workflow_status(
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

    def advance(
        self,
        instance: WorkflowInstance,
        graph: WorkflowGraph,
        *,
        _auto_depth: int = 0,
    ) -> None:
        if instance.status != WorkflowStatus.RUNNING:
            return

        scheduler = GraphScheduler(graph)
        node_instances = {
            node.workflow_node_id: node
            for node in self._instances.list_node_instances(instance.id)
        }
        statuses = {node_id: node.status for node_id, node in node_instances.items()}
        auto_completed = False

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

            if self._auto_runner is not None and self._auto_runner.try_complete(
                instance=instance,
                graph=graph,
                graph_node=graph_node,
                node_instance=node_instance,
            ):
                auto_completed = True

        if auto_completed:
            if _auto_depth >= _MAX_AUTO_ADVANCE_DEPTH:
                raise NodeExecutionError(
                    f"Automatic node cascade exceeded max depth ({_MAX_AUTO_ADVANCE_DEPTH})"
                )
            self.advance(instance, graph, _auto_depth=_auto_depth + 1)
            return

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

    def invalidate_downstream_nodes(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        reason: str,
    ) -> list[WorkflowNodeInstance]:
        instance = self._instances.require_workflow_instance(workflow_instance_id)
        graph = self.load_graph(instance)
        scheduler = GraphScheduler(graph)
        node_instances_by_graph_id = {
            node.workflow_node_id: node
            for node in self._instances.list_node_instances(workflow_instance_id)
        }
        invalidated: list[WorkflowNodeInstance] = []

        for graph_node in scheduler.downstream_task_nodes(workflow_node_id):
            node_instance = node_instances_by_graph_id.get(graph_node.id)
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

        return invalidated

    def transition_to_running(self, instance: WorkflowInstance) -> None:
        self._workflow_sm.transition(instance.status, WorkflowStatus.RUNNING)
        self._instances.update_workflow_status(instance, WorkflowStatus.RUNNING)
