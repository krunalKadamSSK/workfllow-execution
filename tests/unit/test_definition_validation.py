import json
from pathlib import Path

import pytest

from app.domain.validation.graph import validate_graph_topology, validate_node_references
from app.domain.validation.input_wiring import validate_input_wiring
from app.domain.validation.pipeline import validate_workflow_definition
from app.modules.definitions.schemas.nodes import NodeDefinitionIngest
from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest

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
        issues = validate_input_wiring(test_workflow, node_output_fields=node_output_fields)
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
        issues = validate_input_wiring(test_workflow, node_output_fields=node_output_fields)
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
        issues = validate_workflow_definition(
            test_workflow,
            published_node_ids=published_ids,
            node_output_fields=node_output_fields,
        )
        assert issues == []

    def test_missing_node_reference_fails(self, test_workflow: WorkflowDefinitionIngest):
        issues = validate_node_references(test_workflow, published_node_ids=set())
        assert any(issue.code == "UNKNOWN_NODE_DEFINITION" for issue in issues)
