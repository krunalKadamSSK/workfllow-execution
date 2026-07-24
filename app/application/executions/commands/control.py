"""Pause / resume / cancel / reopen / invalidate commands."""

from __future__ import annotations

from app.application.events.event_store import EventStore
from app.application.executions.graph_runtime import GraphRuntime
from app.domain.enums import NodeStatus, WorkflowStatus
from app.domain.events.payloads import NodeInvalidatedPayload
from app.domain.events.types import WorkflowEventType
from app.domain.exceptions import (
    InvalidTransitionError,
    NodeExecutionError,
    VersionConflictError,
)
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.domain.state.workflow import WorkflowStateMachine
from app.infrastructure.persistence.models import WorkflowInstance, WorkflowNodeInstance


class ControlWorkflowCommand:
    """Workflow control-plane mutations (pause, resume, cancel, reopen)."""

    def __init__(
        self,
        *,
        instances: InstanceRepository,
        events: EventStore,
        runtime: GraphRuntime,
    ) -> None:
        self._instances = instances
        self._events = events
        self._runtime = runtime
        self._workflow_sm = WorkflowStateMachine()

    def pause_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        return self._runtime.change_workflow_status(
            workflow_instance_id,
            target=WorkflowStatus.PAUSED,
            event_type=WorkflowEventType.WORKFLOW_PAUSED,
            expected_revision=expected_revision,
        )

    def resume_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        instance = self._runtime.change_workflow_status(
            workflow_instance_id,
            target=WorkflowStatus.RUNNING,
            event_type=WorkflowEventType.WORKFLOW_RESUMED,
            expected_revision=expected_revision,
        )
        self._runtime.advance(instance, self._runtime.load_graph(instance))
        return instance

    def cancel_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        return self._runtime.change_workflow_status(
            workflow_instance_id,
            target=WorkflowStatus.CANCELLED,
            event_type=WorkflowEventType.WORKFLOW_CANCELLED,
            expected_revision=expected_revision,
        )

    def reopen_from_task(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        reason: str,
        expected_revision: int | None = None,
        reopen_target: bool = True,
    ) -> list[WorkflowNodeInstance]:
        instance = self._instances.require_workflow_instance(workflow_instance_id)
        if instance.status not in {WorkflowStatus.RUNNING, WorkflowStatus.COMPLETED}:
            raise InvalidTransitionError(
                f"Cannot reopen task while workflow is {instance.status.value}"
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

        affected: list[WorkflowNodeInstance] = []

        if reopen_target:
            target = self._instances.require_node_instance_by_graph_id(
                workflow_instance_id, workflow_node_id
            )
            if target.status == NodeStatus.COMPLETED:
                self._instances.update_node_status(target, NodeStatus.PENDING)
                self._events.append(
                    workflow_instance_id=workflow_instance_id,
                    event_type=WorkflowEventType.NODE_INVALIDATED.value,
                    payload_json=NodeInvalidatedPayload(
                        workflow_instance_id=workflow_instance_id,
                        workflow_node_instance_id=target.id,
                        workflow_node_id=workflow_node_id,
                        reason=reason,
                    ).to_dict(),
                )
                affected.append(target)
            elif target.status not in {NodeStatus.PENDING, NodeStatus.INVALIDATED}:
                raise InvalidTransitionError(
                    f"Node '{workflow_node_id}' cannot be reopened "
                    f"(status={target.status.value})"
                )

        affected.extend(
            self._runtime.invalidate_downstream_nodes(
                workflow_instance_id=workflow_instance_id,
                workflow_node_id=workflow_node_id,
                reason=reason,
            )
        )

        was_completed = instance.status == WorkflowStatus.COMPLETED
        if was_completed:
            self._workflow_sm.transition(instance.status, WorkflowStatus.RUNNING)
            self._instances.update_workflow_status(instance, WorkflowStatus.RUNNING)
        elif affected:
            self._instances.increment_revision(instance)

        if affected:
            self._runtime.advance(instance, graph)

        return affected

    def invalidate_downstream(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        reason: str,
    ) -> list[WorkflowNodeInstance]:
        return self.reopen_from_task(
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=workflow_node_id,
            reason=reason,
            reopen_target=False,
        )
