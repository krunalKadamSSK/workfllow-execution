"""Concrete mapper: application state → instance HTTP schemas."""

from __future__ import annotations

from app.api.schemas.v1.instances import (
    CurrentTaskResponse,
    ExecutionSummary,
    PendingNodeFormResponse,
    WorkflowInstanceResponse,
    WorkflowInstanceSummaryResponse,
    WorkflowNodeInstanceResponse,
)
from app.domain.enums import NodeStatus


class WorkflowInstanceResponseMapper:
    """Implements ``InstanceResponseMapper``."""

    def resolve_total_cost(self, state: dict) -> float | None:
        projection = state.get("workflow_projection") or {}
        total = projection.get("total")
        if isinstance(total, int | float) and not isinstance(total, bool):
            return float(total)

        summary = state.get("execution_summary") or {}
        summary_total = summary.get("total")
        if isinstance(summary_total, int | float) and not isinstance(summary_total, bool):
            return float(summary_total)

        return None

    def read_instance_metadata(self, instance: object) -> dict:
        raw = getattr(instance, "instance_metadata", None)
        return dict(raw) if isinstance(raw, dict) else {}

    def map_instance_response(self, state: dict) -> WorkflowInstanceResponse:
        instance = state["instance"]
        pending_node_ids = [
            node.workflow_node_id
            for node in state["node_instances"]
            if node.status == NodeStatus.PENDING
        ]
        task_names = state.get("task_names") or {}
        next_task_id = state.get("next_task_id")
        next_task_name = state.get("next_task_name")
        current_task = None
        if next_task_id and next_task_name:
            current_task = CurrentTaskResponse(id=next_task_id, name=next_task_name)

        return WorkflowInstanceResponse(
            id=instance.id,
            name=instance.name,
            workflow_definition_id=instance.workflow_definition_id,
            workflow_definition_version_id=instance.workflow_definition_version_id,
            status=instance.status.value,
            current_revision=instance.current_revision,
            created_at=instance.created_at,
            completed_at=instance.completed_at,
            metadata=self.read_instance_metadata(instance),
            rfq_id=instance.rfq_id,
            node_instances=[
                WorkflowNodeInstanceResponse(
                    id=node.id,
                    workflow_node_id=node.workflow_node_id,
                    node_definition_version_id=node.node_definition_version_id,
                    status=node.status.value,
                    current_execution=node.current_execution,
                    task_name=task_names.get(node.workflow_node_id),
                )
                for node in state["node_instances"]
            ],
            pending_node_ids=pending_node_ids,
            current_task=current_task,
            next_task_id=next_task_id,
            next_task_name=next_task_name,
            task_names=task_names,
            pending_node_forms={
                workflow_node_id: PendingNodeFormResponse(**form)
                for workflow_node_id, form in state.get("pending_node_forms", {}).items()
            },
            workflow_projection=state.get("workflow_projection"),
            execution_summary=(
                ExecutionSummary(**state["execution_summary"])
                if state.get("execution_summary") is not None
                else None
            ),
            total_cost=self.resolve_total_cost(state),
        )

    def map_instance_summary(self, instance: object) -> WorkflowInstanceSummaryResponse:
        return WorkflowInstanceSummaryResponse(
            id=instance.id,
            name=instance.name,
            workflow_definition_id=instance.workflow_definition_id,
            status=instance.status.value,
            current_revision=instance.current_revision,
            created_at=instance.created_at,
            completed_at=instance.completed_at,
            metadata=self.read_instance_metadata(instance),
            rfq_id=instance.rfq_id,
        )
