import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest

FIXTURES = Path(__file__).parent.parent / "fixtures"


def _load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.integration
class TestDefinitionsAPI:
    def test_list_base_types(self, api_client: TestClient):
        response = api_client.get("/api/v1/definitions/base-types")
        assert response.status_code == 200
        kinds = {item["kind"] for item in response.json()}
        assert kinds == {"userInput", "ai", "script"}
        user_input = next(item for item in response.json() if item["kind"] == "userInput")
        assert user_input["displayName"] == "User task"
        assert user_input["enabled"] is True

    def test_publish_and_get_node_definition(self, api_client: TestClient):
        payload = _load("node_general_information.json")
        response = api_client.post("/api/v1/definitions/nodes", json=payload)

        assert response.status_code == 201
        body = response.json()
        assert body["slug"] == "general-information"
        assert body["latest_version"] == 1
        assert body["version"]["definition_json"]["baseKind"] == "userInput"

        get_response = api_client.get("/api/v1/definitions/nodes/general-information")
        assert get_response.status_code == 200
        assert get_response.json()["id"] == payload["id"]

    def test_publish_workflow_with_node_references(self, api_client: TestClient):
        api_client.post("/api/v1/definitions/nodes", json=_load("node_general_information.json"))
        api_client.post("/api/v1/definitions/nodes", json=_load("node_raw_material_pricing.json"))

        workflow_payload = _load("workflow_test.json")
        response = api_client.post("/api/v1/definitions/workflows", json=workflow_payload)

        assert response.status_code == 201
        body = response.json()
        assert body["slug"] == "test-workflow"
        assert len(body["version"]["definition_json"]["nodes"]) == 4

    def test_publish_workflow_without_slug_returns_422(self, api_client: TestClient):
        payload = _load("workflow_test.json")
        payload["slug"] = None
        response = api_client.post("/api/v1/definitions/workflows", json=payload)
        assert response.status_code == 422

    def test_publish_workflow_without_nodes_returns_422(self, api_client: TestClient):
        api_client.post("/api/v1/definitions/nodes", json=_load("node_general_information.json"))
        api_client.post("/api/v1/definitions/nodes", json=_load("node_raw_material_pricing.json"))

        payload = _load("workflow_test.json")
        payload["nodes"] = [node for node in payload["nodes"] if node["kind"] != "start"]
        response = api_client.post("/api/v1/definitions/workflows", json=payload)
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_get_unknown_definition_returns_404(self, api_client: TestClient):
        response = api_client.get("/api/v1/definitions/workflows/does-not-exist")
        assert response.status_code == 404

    def test_list_definitions_returns_summaries(self, api_client: TestClient):
        api_client.post("/api/v1/definitions/nodes", json=_load("node_general_information.json"))
        api_client.post("/api/v1/definitions/nodes", json=_load("node_raw_material_pricing.json"))
        api_client.post("/api/v1/definitions/workflows", json=_load("workflow_test.json"))

        nodes_response = api_client.get("/api/v1/definitions/nodes")
        assert nodes_response.status_code == 200
        node_slugs = {item["slug"] for item in nodes_response.json()}
        assert node_slugs == {"general-information", "raw-material-pricing"}

        workflows_response = api_client.get("/api/v1/definitions/workflows")
        assert workflows_response.status_code == 200
        workflows = workflows_response.json()
        assert len(workflows) == 1
        assert workflows[0]["slug"] == "test-workflow"
        assert "definition_json" not in workflows[0]

    def test_workflow_ingest_model_requires_slug(self):
        payload = _load("workflow_test.json")
        payload["slug"] = None
        with pytest.raises(ValueError):
            WorkflowDefinitionIngest.model_validate(payload)
