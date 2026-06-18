import json
from pathlib import Path

import pytest

from app.application.definitions.ingest import DefinitionIngestService
from app.application.executions.service import ExecutionService
from app.domain.enums import NodeStatus, WorkflowStatus
from app.modules.definitions.schemas.nodes import NodeDefinitionIngest
from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest

FIXTURES = Path(__file__).parent.parent / "fixtures"

GENERAL_INFO_NODE_ID = "4eb5cfe4-8eff-463a-a315-a39f31a26756"
RAW_MATERIAL_NODE_ID = "220b5a4f-de75-45ef-b3bb-8f7f794e301e"
WORKFLOW_ID = "1091df5d-58d8-4233-abd5-0a85ec476470"
GENERAL_INFO_GRAPH_NODE = "c24086be-e3d1-4953-8bbf-6b696b8fdd8e"
RAW_MATERIAL_GRAPH_NODE = "7cf5eaa7-5a13-412b-8bb8-5f6cf386ad68"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def seeded_definitions(db_session):
    ingest = DefinitionIngestService(db_session)
    ingest.publish_node(NodeDefinitionIngest.model_validate(_load("node_general_information.json")))
    ingest.publish_node(NodeDefinitionIngest.model_validate(_load("node_raw_material_pricing.json")))
    ingest.publish_workflow(WorkflowDefinitionIngest.model_validate(_load("workflow_test.json")))
    db_session.flush()
    return ingest


@pytest.mark.integration
class TestWorkflowOrchestrator:
    def test_full_test_workflow_execution(self, db_session, seeded_definitions):
        service = ExecutionService.from_session(db_session)
        instance = service.start_workflow(
            name="Run 1",
            workflow_definition_id=WORKFLOW_ID,
        )
        db_session.flush()

        state = service.get_instance_state(instance.id)
        assert state["instance"].status == WorkflowStatus.RUNNING
        pending_nodes = [
            node for node in state["node_instances"] if node.status == NodeStatus.PENDING
        ]
        assert len(pending_nodes) == 1
        assert pending_nodes[0].workflow_node_id == GENERAL_INFO_GRAPH_NODE

        service.submit_node_outputs(
            workflow_instance_id=instance.id,
            workflow_node_id=GENERAL_INFO_GRAPH_NODE,
            outputs={
                "customerName": "ACME",
                "partName": "PART-1",
                "castingProcess": "GDC",
                "volume": 10,
            },
        )
        db_session.flush()

        state = service.get_instance_state(instance.id)
        pending_nodes = [
            node for node in state["node_instances"] if node.status == NodeStatus.PENDING
        ]
        assert len(pending_nodes) == 1
        assert pending_nodes[0].workflow_node_id == RAW_MATERIAL_GRAPH_NODE

        service.submit_node_outputs(
            workflow_instance_id=instance.id,
            workflow_node_id=RAW_MATERIAL_GRAPH_NODE,
            outputs={
                "customerName": "ACME",
                "partName": "PART-1",
                "meltLossPercentage": 5,
                "rawWeight": 10,
                "inputWeight": 15,
            },
        )
        db_session.flush()

        state = service.get_instance_state(instance.id)
        assert state["instance"].status == WorkflowStatus.COMPLETED
        projection = state["workflow_projection"]
        assert projection is not None
        assert projection["status"] == WorkflowStatus.COMPLETED.value
        assert projection["nodes"][RAW_MATERIAL_GRAPH_NODE]["outputs"]["inputWeight"] == 15

        events = service.list_events(instance.id)
        event_types = [event.event_type for event in events]
        assert "WORKFLOW_STARTED" in event_types
        assert "NODE_COMPLETED" in event_types
        assert "WORKFLOW_COMPLETED" in event_types

    def test_submit_before_ready_returns_conflict(self, db_session, seeded_definitions):
        service = ExecutionService.from_session(db_session)
        instance = service.start_workflow(
            name="Run 2",
            workflow_definition_id=WORKFLOW_ID,
        )
        db_session.flush()

        from app.domain.exceptions import UpstreamNotReadyError

        with pytest.raises(UpstreamNotReadyError):
            service.submit_node_outputs(
                workflow_instance_id=instance.id,
                workflow_node_id=RAW_MATERIAL_GRAPH_NODE,
                outputs={"customerName": "ACME"},
            )

    def test_pause_and_resume_workflow(self, db_session, seeded_definitions):
        service = ExecutionService.from_session(db_session)
        instance = service.start_workflow(
            name="Run 3",
            workflow_definition_id=WORKFLOW_ID,
        )
        db_session.flush()

        paused = service.pause_workflow(instance.id)
        db_session.flush()
        assert paused.status == WorkflowStatus.PAUSED

        resumed = service.resume_workflow(instance.id)
        db_session.flush()
        assert resumed.status == WorkflowStatus.RUNNING
