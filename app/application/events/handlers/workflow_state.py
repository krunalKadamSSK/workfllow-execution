from __future__ import annotations

import copy
from typing import Any

from app.domain.enums import WorkflowStatus
from app.domain.events.stored_event import StoredEvent
from app.domain.events.types import WorkflowEventType


def initial_workflow_state() -> dict[str, Any]:
    return {
        "status": WorkflowStatus.PENDING.value,
        "last_sequence": 0,
        "nodes": {},
        "total": None,
    }


def apply_workflow_projection_event(state: dict[str, Any], event: StoredEvent) -> dict[str, Any]:
    """Pure reducer for workflow-level projection state."""
    next_state = copy.deepcopy(state)
    next_state["last_sequence"] = event.sequence_number
    payload = event.payload_json

    if event.event_type == WorkflowEventType.WORKFLOW_STARTED.value:
        next_state["status"] = WorkflowStatus.RUNNING.value
        next_state["workflow_definition_id"] = payload["workflow_definition_id"]
        next_state["workflow_definition_version_id"] = payload["workflow_definition_version_id"]
        return next_state

    if event.event_type == WorkflowEventType.WORKFLOW_PAUSED.value:
        next_state["status"] = WorkflowStatus.PAUSED.value
        return next_state

    if event.event_type == WorkflowEventType.WORKFLOW_RESUMED.value:
        next_state["status"] = WorkflowStatus.RUNNING.value
        return next_state

    if event.event_type == WorkflowEventType.WORKFLOW_COMPLETED.value:
        next_state["status"] = WorkflowStatus.COMPLETED.value
        return next_state

    if event.event_type == WorkflowEventType.WORKFLOW_CANCELLED.value:
        next_state["status"] = WorkflowStatus.CANCELLED.value
        return next_state

    if event.event_type == WorkflowEventType.NODE_READY.value:
        _upsert_node_state(
            next_state,
            workflow_node_id=payload["workflow_node_id"],
            workflow_node_instance_id=payload["workflow_node_instance_id"],
            status="PENDING",
        )
        return next_state

    if event.event_type == WorkflowEventType.NODE_STARTED.value:
        _upsert_node_state(
            next_state,
            workflow_node_id=payload["workflow_node_id"],
            workflow_node_instance_id=payload["workflow_node_instance_id"],
            status="RUNNING",
            execution_number=payload.get("execution_number"),
        )
        return next_state

    if event.event_type == WorkflowEventType.NODE_COMPLETED.value:
        node_updates: dict[str, Any] = {
            "workflow_node_instance_id": payload["workflow_node_instance_id"],
            "status": "COMPLETED",
            "execution_number": payload.get("execution_number"),
            "outputs": payload.get("outputs", {}),
        }
        cost_contribution = payload.get("cost_contribution")
        if cost_contribution is not None:
            node_updates["cost_contribution"] = cost_contribution
        _upsert_node_state(
            next_state,
            workflow_node_id=payload["workflow_node_id"],
            **node_updates,
        )
        _recompute_total(next_state)
        return next_state

    if event.event_type == WorkflowEventType.NODE_FAILED.value:
        _upsert_node_state(
            next_state,
            workflow_node_id=payload["workflow_node_id"],
            workflow_node_instance_id=payload["workflow_node_instance_id"],
            status="FAILED",
            execution_number=payload.get("execution_number"),
            error_message=payload.get("error_message"),
        )
        return next_state

    if event.event_type == WorkflowEventType.NODE_INVALIDATED.value:
        _upsert_node_state(
            next_state,
            workflow_node_id=payload["workflow_node_id"],
            workflow_node_instance_id=payload["workflow_node_instance_id"],
            status="INVALIDATED",
            reason=payload.get("reason"),
        )
        _recompute_total(next_state)
        return next_state

    return next_state


def _recompute_total(state: dict[str, Any]) -> None:
    total = 0.0
    found = False
    for node in state.get("nodes", {}).values():
        if node.get("status") != "COMPLETED":
            continue
        contribution = node.get("cost_contribution")
        if isinstance(contribution, bool):
            continue
        if isinstance(contribution, (int, float)):
            total += float(contribution)
            found = True
    state["total"] = total if found else None


def _upsert_node_state(state: dict[str, Any], *, workflow_node_id: str, **updates: Any) -> None:
    nodes = state.setdefault("nodes", {})
    node_state = dict(nodes.get(workflow_node_id, {}))
    node_state["workflow_node_id"] = workflow_node_id
    node_state.update({key: value for key, value in updates.items() if value is not None})
    nodes[workflow_node_id] = node_state
