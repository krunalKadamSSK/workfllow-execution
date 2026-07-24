import json
from pathlib import Path

import pytest

from app.api.schemas.v1.definitions.nodes import NodeDefinitionIngest
from app.api.schemas.v1.definitions.workflows import WorkflowDefinitionIngest
from app.domain.validation.graph import validate_graph_topology, validate_node_references
from app.domain.validation.input_wiring import validate_input_wiring
from app.domain.validation.pipeline import validate_workflow_definition

FIXTURES = Path(__file__).parent.parent / "fixtures"


def load_json(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def general_information_node() -> NodeDefinitionIngest:
    return NodeDefinitionIngest.model_validate(load_json("node_general_information.json"))


@pytest.fixture
def raw_material_pricing_node() -> NodeDefinitionIngest:
    return NodeDefinitionIngest.model_validate(load_json("node_raw_material_pricing.json"))


@pytest.fixture
def test_workflow() -> WorkflowDefinitionIngest:
    return WorkflowDefinitionIngest.model_validate(load_json("workflow_test.json"))


class TestGraphTopologyValidator:
    def test_valid_workflow_passes(self, test_workflow: WorkflowDefinitionIngest):
        issues = validate_graph_topology(test_workflow)
        assert issues == []

    def test_missing_start_node_fails(self, test_workflow: WorkflowDefinitionIngest):
        test_workflow.nodes = [node for node in test_workflow.nodes if node.kind != "start"]
        issues = validate_graph_topology(test_workflow)
        assert any(issue.code == "INVALID_START_NODE" for issue in issues)

    def test_cycle_fails(self, test_workflow: WorkflowDefinitionIngest):
        test_workflow.edges.append(
            test_workflow.edges[0].model_copy(
                update={
                    "id": "cycle-edge",
                    "source": "af0b00c0-e762-4fff-9a97-36e9e0d12138",
                    "target": "92579c4a-314e-418a-97a4-2a2972ced2e0",
                }
            )
        )
        issues = validate_graph_topology(test_workflow)
        assert any(issue.code == "CYCLIC_GRAPH" for issue in issues)


class TestInputWiringValidator:
    def test_valid_upstream_wiring_passes(
        self,
        test_workflow: WorkflowDefinitionIngest,
        general_information_node: NodeDefinitionIngest,
        raw_material_pricing_node: NodeDefinitionIngest,
    ):
        node_output_fields = {
            general_information_node.id: general_information_node.output_field_ids(),
            raw_material_pricing_node.id: raw_material_pricing_node.output_field_ids(),
        }
        node_input_fields = {
            general_information_node.id: general_information_node.input_field_ids(),
            raw_material_pricing_node.id: raw_material_pricing_node.input_field_ids(),
        }
        issues = validate_input_wiring(
            test_workflow,
            node_output_fields=node_output_fields,
            node_input_fields=node_input_fields,
        )
        assert issues == []

    def test_unknown_output_key_fails(
        self,
        test_workflow: WorkflowDefinitionIngest,
        general_information_node: NodeDefinitionIngest,
        raw_material_pricing_node: NodeDefinitionIngest,
    ):
        node_output_fields = {
            general_information_node.id: {"customerName"},
            raw_material_pricing_node.id: raw_material_pricing_node.output_field_ids(),
        }
        issues = validate_input_wiring(
            test_workflow,
            node_output_fields=node_output_fields,
            node_input_fields=node_output_fields,
        )
        assert any(issue.code == "UNKNOWN_OUTPUT_KEY" for issue in issues)


class TestWorkflowValidationPipeline:
    def test_pipeline_passes_with_published_nodes(
        self,
        test_workflow: WorkflowDefinitionIngest,
        general_information_node: NodeDefinitionIngest,
        raw_material_pricing_node: NodeDefinitionIngest,
    ):
        published_ids = {general_information_node.id, raw_material_pricing_node.id}
        node_output_fields = {
            general_information_node.id: general_information_node.output_field_ids(),
            raw_material_pricing_node.id: raw_material_pricing_node.output_field_ids(),
        }
        node_input_fields = {
            general_information_node.id: general_information_node.input_field_ids(),
            raw_material_pricing_node.id: raw_material_pricing_node.input_field_ids(),
        }
        issues = validate_workflow_definition(
            test_workflow,
            published_node_ids=published_ids,
            node_output_fields=node_output_fields,
            node_input_fields=node_input_fields,
        )
        assert issues == []

    def test_missing_node_reference_fails(self, test_workflow: WorkflowDefinitionIngest):
        issues = validate_node_references(test_workflow, published_node_ids=set())
        assert any(issue.code == "UNKNOWN_NODE_DEFINITION" for issue in issues)


def test_workflow_task_node_name_is_stored_as_label():
    payload = load_json("workflow_test.json")
    task_node = payload["nodes"][1]
    task_node.pop("label", None)
    task_node["name"] = "General information"

    workflow = WorkflowDefinitionIngest.model_validate(payload)
    stored_task = workflow.to_stored_json()["nodes"][1]

    assert stored_task["label"] == "General information"


def test_table_column_input_key_is_valid_input():
    from app.domain.definitions.table_fields import table_column_input_key

    table_node = NodeDefinitionIngest.model_validate(
        {
            "id": "table-node-1",
            "name": "Table",
            "slug": "table-node",
            "status": "published",
            "version": "1",
            "baseKind": "table",
            "appearance": {
                "icon": {"kind": "lucide", "name": "table"},
                "color": {"kind": "token", "value": "blue"},
                "shape": "card",
                "badge": "Table",
            },
            "table": {
                "columns": [{"id": "customer_name", "type": "text", "label": "Customer"}],
            },
            "aggregations": [],
        }
    )
    user_input_node = NodeDefinitionIngest.model_validate(
        load_json("node_general_information.json")
    )

    workflow = WorkflowDefinitionIngest.model_validate(
        {
            "id": "wf-1",
            "name": "Table workflow",
            "slug": "table-workflow",
            "status": "draft",
            "version": "1",
            "nodes": [
                {"id": "start-1", "kind": "start", "position": {"x": 0, "y": 0}},
                {
                    "id": "upstream-1",
                    "kind": "task",
                    "nodeDefinitionId": user_input_node.id,
                    "position": {"x": 100, "y": 0},
                },
                {
                    "id": "table-1",
                    "kind": "task",
                    "nodeDefinitionId": table_node.id,
                    "position": {"x": 200, "y": 0},
                    "inputs": [
                        {
                            "inputKey": table_column_input_key("customer_name"),
                            "source": {
                                "kind": "upstream",
                                "sourceNodeId": "upstream-1",
                                "outputKey": "customerName",
                            },
                        }
                    ],
                },
                {"id": "end-1", "kind": "end", "position": {"x": 300, "y": 0}},
            ],
            "edges": [
                {"id": "e1", "source": "start-1", "target": "upstream-1"},
                {"id": "e2", "source": "upstream-1", "target": "table-1"},
                {"id": "e3", "source": "table-1", "target": "end-1"},
            ],
        }
    )

    issues = validate_input_wiring(
        workflow,
        node_output_fields={
            user_input_node.id: user_input_node.output_field_ids(),
            table_node.id: table_node.output_field_ids(),
        },
        node_input_fields={
            user_input_node.id: user_input_node.input_field_ids(),
            table_node.id: table_node.input_field_ids(),
        },
    )
    assert issues == []
