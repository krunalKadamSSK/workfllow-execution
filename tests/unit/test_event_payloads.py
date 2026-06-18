from app.domain.events import (
    NodeCompletedPayload,
    NodeReadyPayload,
    WorkflowEventType,
    WorkflowStartedPayload,
)


def test_workflow_event_types_are_strings():
    assert WorkflowEventType.WORKFLOW_STARTED.value == "WORKFLOW_STARTED"
    assert WorkflowEventType.NODE_COMPLETED.value == "NODE_COMPLETED"


def test_workflow_started_payload_roundtrip():
    payload = WorkflowStartedPayload(
        workflow_instance_id="inst-1",
        workflow_definition_id="def-1",
        workflow_definition_version_id="ver-1",
    )
    data = payload.to_dict()
    assert data["workflow_instance_id"] == "inst-1"
    assert data["workflow_definition_version_id"] == "ver-1"


def test_node_ready_payload_roundtrip():
    payload = NodeReadyPayload(
        workflow_instance_id="inst-1",
        workflow_node_instance_id="node-inst-1",
        workflow_node_id="graph-node-1",
        node_definition_version_id="ver-1",
    )
    assert payload.to_dict()["workflow_node_id"] == "graph-node-1"


def test_node_completed_payload_includes_outputs():
    payload = NodeCompletedPayload(
        workflow_instance_id="inst-1",
        workflow_node_instance_id="node-inst-1",
        workflow_node_id="graph-node-1",
        execution_number=1,
        outputs={"customerName": "ACME"},
    )
    assert payload.to_dict()["outputs"]["customerName"] == "ACME"
