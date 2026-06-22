from app.application.events.handlers.workflow_state import (
    apply_workflow_projection_event,
    initial_workflow_state,
)
from app.domain.events.stored_event import StoredEvent
from app.domain.events.types import WorkflowEventType


def _event(event_type: str, payload: dict, sequence: int = 1) -> StoredEvent:
    return StoredEvent(
        id="evt",
        workflow_instance_id="inst-1",
        sequence_number=sequence,
        event_type=event_type,
        payload_json=payload,
    )


def test_workflow_started_sets_running_status():
    state = apply_workflow_projection_event(
        initial_workflow_state(),
        _event(
            WorkflowEventType.WORKFLOW_STARTED.value,
            {
                "workflow_definition_id": "def-1",
                "workflow_definition_version_id": "ver-1",
            },
        ),
    )
    assert state["status"] == "RUNNING"
    assert state["workflow_definition_id"] == "def-1"


def test_node_completed_updates_node_map():
    state = initial_workflow_state()
    state = apply_workflow_projection_event(
        state,
        _event(
            WorkflowEventType.NODE_COMPLETED.value,
            {
                "workflow_node_id": "node-1",
                "workflow_node_instance_id": "node-inst-1",
                "execution_number": 1,
                "outputs": {"customerName": "ACME"},
            },
            sequence=2,
        ),
    )
    assert state["nodes"]["node-1"]["status"] == "COMPLETED"
    assert state["nodes"]["node-1"]["outputs"]["customerName"] == "ACME"
    assert state["last_sequence"] == 2
    assert state["total"] is None


def test_node_completed_accumulates_total_from_cost_contribution():
    state = initial_workflow_state()
    state = apply_workflow_projection_event(
        state,
        _event(
            WorkflowEventType.NODE_COMPLETED.value,
            {
                "workflow_node_id": "node-1",
                "workflow_node_instance_id": "node-inst-1",
                "execution_number": 1,
                "outputs": {"inputWeight": 15},
                "cost_contribution": 15,
            },
            sequence=2,
        ),
    )
    assert state["nodes"]["node-1"]["cost_contribution"] == 15
    assert state["total"] == 15.0

    state = apply_workflow_projection_event(
        state,
        _event(
            WorkflowEventType.NODE_COMPLETED.value,
            {
                "workflow_node_id": "node-2",
                "workflow_node_instance_id": "node-inst-2",
                "execution_number": 1,
                "outputs": {"lineTotal": 25},
                "cost_contribution": 25,
            },
            sequence=3,
        ),
    )
    assert state["total"] == 40.0


def test_node_completed_accumulates_float_cost_contributions():
    state = initial_workflow_state()
    state = apply_workflow_projection_event(
        state,
        _event(
            WorkflowEventType.NODE_COMPLETED.value,
            {
                "workflow_node_id": "node-1",
                "workflow_node_instance_id": "node-inst-1",
                "execution_number": 1,
                "outputs": {"inputWeight": 10.5},
                "cost_contribution": 10.5,
            },
            sequence=2,
        ),
    )
    state = apply_workflow_projection_event(
        state,
        _event(
            WorkflowEventType.NODE_COMPLETED.value,
            {
                "workflow_node_id": "node-2",
                "workflow_node_instance_id": "node-inst-2",
                "execution_number": 1,
                "outputs": {"lineTotal": 4.25},
                "cost_contribution": 4.25,
            },
            sequence=3,
        ),
    )
    assert state["total"] == 14.75


def test_node_invalidated_recomputes_total():
    state = initial_workflow_state()
    state = apply_workflow_projection_event(
        state,
        _event(
            WorkflowEventType.NODE_COMPLETED.value,
            {
                "workflow_node_id": "node-1",
                "workflow_node_instance_id": "node-inst-1",
                "execution_number": 1,
                "outputs": {"inputWeight": 15},
                "cost_contribution": 15,
            },
            sequence=2,
        ),
    )
    state = apply_workflow_projection_event(
        state,
        _event(
            WorkflowEventType.NODE_COMPLETED.value,
            {
                "workflow_node_id": "node-2",
                "workflow_node_instance_id": "node-inst-2",
                "execution_number": 1,
                "outputs": {"lineTotal": 25},
                "cost_contribution": 25,
            },
            sequence=3,
        ),
    )
    state = apply_workflow_projection_event(
        state,
        _event(
            WorkflowEventType.NODE_INVALIDATED.value,
            {
                "workflow_node_id": "node-2",
                "workflow_node_instance_id": "node-inst-2",
                "reason": "upstream changed",
            },
            sequence=4,
        ),
    )
    assert state["nodes"]["node-2"]["status"] == "INVALIDATED"
    assert state["total"] == 15.0


def test_workflow_completed_sets_terminal_status():
    state = apply_workflow_projection_event(
        initial_workflow_state(),
        _event(WorkflowEventType.WORKFLOW_COMPLETED.value, {}),
    )
    assert state["status"] == "COMPLETED"
