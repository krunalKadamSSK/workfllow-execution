import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

FIXTURES = Path(__file__).parent.parent / "fixtures"

WORKFLOW_ID = "1091df5d-58d8-4233-abd5-0a85ec476470"
GENERAL_INFO_GRAPH_NODE = "c24086be-e3d1-4953-8bbf-6b696b8fdd8e"
RAW_MATERIAL_GRAPH_NODE = "7cf5eaa7-5a13-412b-8bb8-5f6cf386ad68"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


def _seed_definitions(api_client: TestClient) -> None:
    api_client.post("/api/v1/definitions/nodes", json=_load("node_general_information.json"))
    api_client.post("/api/v1/definitions/nodes", json=_load("node_raw_material_pricing.json"))
    api_client.post("/api/v1/definitions/workflows", json=_load("workflow_test.json"))


def _assert_error_shape(response, *, status_code: int, code: str) -> None:
    assert response.status_code == status_code
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == code
    assert "message" in body["error"]
    assert "details" in body["error"]
    assert "request_id" in body["error"]


@pytest.mark.integration
class TestExecutionsAPI:
    def test_start_get_and_complete_workflow(self, api_client: TestClient):
        _seed_definitions(api_client)

        start_response = api_client.post(
            "/api/v1/instances",
            json={"name": "API Run 1", "workflow_definition_id": WORKFLOW_ID},
        )
        assert start_response.status_code == 201
        instance = start_response.json()
        instance_id = instance["id"]
        assert instance["status"] == "RUNNING"
        assert instance["pending_node_ids"] == [GENERAL_INFO_GRAPH_NODE]
        assert instance["next_task_id"] == GENERAL_INFO_GRAPH_NODE
        assert GENERAL_INFO_GRAPH_NODE not in instance["pending_node_forms"]

        get_response = api_client.get(f"/api/v1/instances/{instance_id}")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == instance_id

        submit_one = api_client.post(
            f"/api/v1/instances/{instance_id}/nodes/{GENERAL_INFO_GRAPH_NODE}/submit",
            json={
                "outputs": {
                    "customerName": "ACME",
                    "partName": "PART-1",
                    "castingProcess": "GDC",
                    "volume": 10,
                }
            },
        )
        assert submit_one.status_code == 200
        assert submit_one.json()["pending_node_ids"] == [RAW_MATERIAL_GRAPH_NODE]
        assert submit_one.json()["next_task_id"] == RAW_MATERIAL_GRAPH_NODE
        pricing_form = submit_one.json()["pending_node_forms"][RAW_MATERIAL_GRAPH_NODE]["fields"]
        pricing_fields = {field["id"]: field for field in pricing_form}
        assert pricing_fields["customerName"]["defaultValue"] == "ACME"
        assert pricing_fields["partName"]["defaultValue"] == "PART-1"

        submit_two = api_client.post(
            f"/api/v1/instances/{instance_id}/nodes/{RAW_MATERIAL_GRAPH_NODE}/submit",
            json={
                "outputs": {
                    "customerName": "ACME",
                    "partName": "PART-1",
                    "meltLossPercentage": 5,
                    "rawWeight": 10,
                    "inputWeight": 15,
                }
            },
        )
        assert submit_two.status_code == 200
        completed = submit_two.json()
        assert completed["status"] == "COMPLETED"
        assert completed["pending_node_ids"] == []
        assert completed["next_task_id"] is None
        assert (
            completed["workflow_projection"]["nodes"][RAW_MATERIAL_GRAPH_NODE]["outputs"][
                "inputWeight"
            ]
            == 15
        )

        events_response = api_client.get(f"/api/v1/instances/{instance_id}/events")
        assert events_response.status_code == 200
        event_types = [event["event_type"] for event in events_response.json()]
        assert "WORKFLOW_STARTED" in event_types
        assert "NODE_COMPLETED" in event_types
        assert "WORKFLOW_COMPLETED" in event_types

    def test_get_unknown_instance_returns_404(self, api_client: TestClient):
        response = api_client.get("/api/v1/instances/does-not-exist")
        _assert_error_shape(response, status_code=404, code="NOT_FOUND")

    def test_start_unknown_workflow_returns_404(self, api_client: TestClient):
        response = api_client.post(
            "/api/v1/instances",
            json={"name": "Bad", "workflow_definition_id": "missing-workflow-id"},
        )
        _assert_error_shape(response, status_code=404, code="NOT_FOUND")

    def test_submit_before_ready_returns_409(self, api_client: TestClient):
        _seed_definitions(api_client)
        start_response = api_client.post(
            "/api/v1/instances",
            json={"name": "API Run 2", "workflow_definition_id": WORKFLOW_ID},
        )
        instance_id = start_response.json()["id"]

        response = api_client.post(
            f"/api/v1/instances/{instance_id}/nodes/{RAW_MATERIAL_GRAPH_NODE}/submit",
            json={"outputs": {"customerName": "ACME"}},
        )
        _assert_error_shape(response, status_code=409, code="UPSTREAM_NOT_READY")

    def test_submit_invalid_outputs_returns_400(self, api_client: TestClient):
        _seed_definitions(api_client)
        start_response = api_client.post(
            "/api/v1/instances",
            json={"name": "API Run 3", "workflow_definition_id": WORKFLOW_ID},
        )
        instance_id = start_response.json()["id"]

        response = api_client.post(
            f"/api/v1/instances/{instance_id}/nodes/{GENERAL_INFO_GRAPH_NODE}/submit",
            json={"outputs": {"customerName": "ACME"}},
        )
        _assert_error_shape(response, status_code=400, code="FIELD_VALIDATION_FAILED")

    def test_revision_conflict_returns_409(self, api_client: TestClient):
        _seed_definitions(api_client)
        start_response = api_client.post(
            "/api/v1/instances",
            json={"name": "API Run 4", "workflow_definition_id": WORKFLOW_ID},
        )
        instance_id = start_response.json()["id"]

        response = api_client.post(
            f"/api/v1/instances/{instance_id}/nodes/{GENERAL_INFO_GRAPH_NODE}/submit",
            json={
                "outputs": {
                    "customerName": "ACME",
                    "partName": "PART-1",
                    "castingProcess": "GDC",
                    "volume": 10,
                },
                "expected_revision": 999,
            },
        )
        _assert_error_shape(response, status_code=409, code="VERSION_CONFLICT")

    def test_pause_and_resume_workflow(self, api_client: TestClient):
        _seed_definitions(api_client)
        start_response = api_client.post(
            "/api/v1/instances",
            json={"name": "API Run 5", "workflow_definition_id": WORKFLOW_ID},
        )
        instance_id = start_response.json()["id"]

        pause_response = api_client.post(f"/api/v1/instances/{instance_id}/pause")
        assert pause_response.status_code == 200
        assert pause_response.json()["status"] == "PAUSED"

        resume_response = api_client.post(f"/api/v1/instances/{instance_id}/resume")
        assert resume_response.status_code == 200
        assert resume_response.json()["status"] == "RUNNING"

    def test_request_validation_error_shape(self, api_client: TestClient):
        response = api_client.post("/api/v1/instances", json={})
        _assert_error_shape(response, status_code=422, code="VALIDATION_ERROR")
