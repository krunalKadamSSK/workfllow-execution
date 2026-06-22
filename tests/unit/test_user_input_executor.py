import json
from pathlib import Path

import pytest

from app.application.executions.in_memory_projections import InMemoryNodeProjectionReader
from app.application.executions.input_binder import GraphInputBinder
from app.application.executions.upstream_resolver import UpstreamInputResolver
from app.domain.exceptions import FieldValidationError, InputResolutionError
from app.domain.executors.user_input import UserInputExecutor
from app.domain.graph import WorkflowGraph
from app.domain.ports.executors import ExecutionContext

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def workflow_graph() -> WorkflowGraph:
    data = json.loads((FIXTURES / "workflow_test.json").read_text())
    return WorkflowGraph.from_definition_json(
        {"description": data.get("description"), "nodes": data["nodes"], "edges": data["edges"]}
    )


@pytest.fixture
def general_info_definition() -> dict:
    return json.loads((FIXTURES / "node_general_information.json").read_text())


@pytest.fixture
def raw_material_definition() -> dict:
    payload = json.loads((FIXTURES / "node_raw_material_pricing.json").read_text())
    return {
        "baseKind": payload["baseKind"],
        "appearance": payload["appearance"],
        "description": payload.get("description"),
        "output": payload.get("output"),
        "form": payload["form"],
    }


class TestUpstreamInputResolver:
    def test_resolves_upstream_output(self):
        reader = InMemoryNodeProjectionReader()
        reader.set_values(
            workflow_instance_id="inst-1",
            workflow_node_id="c24086be-e3d1-4953-8bbf-6b696b8fdd8e",
            values={"customerName": "ACME", "partName": "PART-1"},
        )
        resolver = UpstreamInputResolver(reader)

        value = resolver.resolve(
            workflow_instance_id="inst-1",
            source_node_id="c24086be-e3d1-4953-8bbf-6b696b8fdd8e",
            output_key="customerName",
        )
        assert value == "ACME"

    def test_missing_projection_raises(self):
        resolver = UpstreamInputResolver(InMemoryNodeProjectionReader())
        with pytest.raises(InputResolutionError):
            resolver.resolve(
                workflow_instance_id="inst-1",
                source_node_id="missing",
                output_key="customerName",
            )


class TestGraphInputBinder:
    def test_binds_locked_upstream_inputs(
        self, workflow_graph: WorkflowGraph, general_info_definition: dict
    ):
        reader = InMemoryNodeProjectionReader()
        reader.set_values(
            workflow_instance_id="inst-1",
            workflow_node_id="c24086be-e3d1-4953-8bbf-6b696b8fdd8e",
            values={"customerName": "ACME", "partName": "PART-1"},
        )
        binder = GraphInputBinder(UpstreamInputResolver(reader))
        pricing_node = workflow_graph.task_nodes[1]

        resolved = binder.resolve(workflow_instance_id="inst-1", graph_node=pricing_node)

        assert resolved.values == {"customerName": "ACME", "partName": "PART-1"}
        assert resolved.locked_keys == frozenset({"customerName", "partName"})


class TestUserInputExecutor:
    def test_general_information_node_submission(
        self, general_info_definition: dict, workflow_graph: WorkflowGraph
    ):
        executor = UserInputExecutor()
        first_task = workflow_graph.task_nodes[0]
        context = ExecutionContext(
            workflow_instance_id="inst-1",
            workflow_node_instance_id="node-inst-1",
            workflow_node_id=first_task.id,
            node_definition_version_id="ver-1",
            base_kind="userInput",
            definition_json=general_info_definition,
        )
        outputs = executor.run(
            context,
            {
                "customerName": "ACME",
                "partName": "PART-1",
                "castingProcess": "GDC",
                "volume": 100,
            },
        )
        assert outputs["customerName"] == "ACME"
        assert outputs["volume"] == 100

    def test_raw_material_node_with_upstream_locked_inputs(
        self,
        workflow_graph: WorkflowGraph,
        raw_material_definition: dict,
    ):
        reader = InMemoryNodeProjectionReader()
        upstream_node_id = "c24086be-e3d1-4953-8bbf-6b696b8fdd8e"
        reader.set_values(
            workflow_instance_id="inst-1",
            workflow_node_id=upstream_node_id,
            values={"customerName": "ACME", "partName": "PART-1"},
        )
        binder = GraphInputBinder(UpstreamInputResolver(reader))
        pricing_node = workflow_graph.task_nodes[1]
        resolved = binder.resolve(workflow_instance_id="inst-1", graph_node=pricing_node)

        executor = UserInputExecutor()
        context = ExecutionContext(
            workflow_instance_id="inst-1",
            workflow_node_instance_id="node-inst-2",
            workflow_node_id=pricing_node.id,
            node_definition_version_id="ver-2",
            base_kind="userInput",
            definition_json=raw_material_definition,
            resolved_inputs=resolved.values,
            locked_input_keys=resolved.locked_keys,
        )

        outputs = executor.run(
            context,
            {
                "customerName": "ACME",
                "partName": "PART-1",
                "meltLossPercentage": 5,
                "rawWeight": 10,
                "inputWeight": 15,
            },
        )

        assert outputs["customerName"] == "ACME"
        assert outputs["inputWeight"] == 15

    def test_locked_input_modification_rejected(
        self, raw_material_definition: dict, workflow_graph: WorkflowGraph
    ):
        pricing_node = workflow_graph.task_nodes[1]
        executor = UserInputExecutor()
        context = ExecutionContext(
            workflow_instance_id="inst-1",
            workflow_node_instance_id="node-inst-2",
            workflow_node_id=pricing_node.id,
            node_definition_version_id="ver-2",
            base_kind="userInput",
            definition_json=raw_material_definition,
            resolved_inputs={"customerName": "ACME", "partName": "PART-1"},
            locked_input_keys=frozenset({"customerName"}),
        )

        with pytest.raises(FieldValidationError, match="Locked upstream inputs"):
            executor.run(
                context,
                {
                    "customerName": "OTHER",
                    "partName": "PART-1",
                    "meltLossPercentage": 5,
                    "rawWeight": 10,
                    "inputWeight": 15,
                },
            )

    def test_declared_output_required_when_configured(self, raw_material_definition: dict):
        executor = UserInputExecutor()
        context = ExecutionContext(
            workflow_instance_id="inst-1",
            workflow_node_instance_id="node-inst-2",
            workflow_node_id="node-2",
            node_definition_version_id="ver-2",
            base_kind="userInput",
            definition_json=raw_material_definition,
        )

        with pytest.raises(FieldValidationError) as exc_info:
            executor.run(
                context,
                {
                    "customerName": "ACME",
                    "partName": "PART-1",
                    "meltLossPercentage": 5,
                    "rawWeight": 10,
                },
            )
        assert any(error["field"] == "inputWeight" for error in exc_info.value.details)

    def test_declared_output_must_be_numeric(self, raw_material_definition: dict):
        executor = UserInputExecutor()
        context = ExecutionContext(
            workflow_instance_id="inst-1",
            workflow_node_instance_id="node-inst-2",
            workflow_node_id="node-2",
            node_definition_version_id="ver-2",
            base_kind="userInput",
            definition_json=raw_material_definition,
        )

        with pytest.raises(FieldValidationError) as exc_info:
            executor.run(
                context,
                {
                    "customerName": "ACME",
                    "partName": "PART-1",
                    "meltLossPercentage": 5,
                    "rawWeight": 10,
                    "inputWeight": "15.5",
                },
            )
        assert any(
            error["field"] == "inputWeight" and error["rule"] == "number"
            for error in exc_info.value.details
        )

    def test_declared_output_accepts_float(self, raw_material_definition: dict):
        executor = UserInputExecutor()
        context = ExecutionContext(
            workflow_instance_id="inst-1",
            workflow_node_instance_id="node-inst-2",
            workflow_node_id="node-2",
            node_definition_version_id="ver-2",
            base_kind="userInput",
            definition_json=raw_material_definition,
        )

        outputs = executor.run(
            context,
            {
                "customerName": "ACME",
                "partName": "PART-1",
                "meltLossPercentage": 5,
                "rawWeight": 10,
                "inputWeight": 15.5,
            },
        )
        assert outputs["inputWeight"] == 15.5

    def test_prepare_sets_upstream_defaults(self, raw_material_definition: dict):
        executor = UserInputExecutor()
        context = ExecutionContext(
            workflow_instance_id="inst-1",
            workflow_node_instance_id="node-inst-2",
            workflow_node_id="node-2",
            node_definition_version_id="ver-2",
            base_kind="userInput",
            definition_json=raw_material_definition,
            resolved_inputs={"customerName": "ACME", "partName": "PART-1"},
            locked_input_keys=frozenset({"customerName", "partName"}),
        )

        prepared = executor.prepare(context)
        assert prepared == {"customerName": "ACME", "partName": "PART-1"}

    def test_prepare_form_fields_adds_default_value_for_upstream_fields(
        self, raw_material_definition: dict
    ):
        executor = UserInputExecutor()
        context = ExecutionContext(
            workflow_instance_id="inst-1",
            workflow_node_instance_id="node-inst-2",
            workflow_node_id="node-2",
            node_definition_version_id="ver-2",
            base_kind="userInput",
            definition_json=raw_material_definition,
            resolved_inputs={"customerName": "ACME", "partName": "PART-1"},
            locked_input_keys=frozenset({"customerName", "partName"}),
        )

        fields = executor.prepare_form_fields(context)
        by_id = {field["id"]: field for field in fields}

        assert by_id["customerName"]["defaultValue"] == "ACME"
        assert by_id["partName"]["defaultValue"] == "PART-1"
        assert "defaultValue" not in by_id["meltLossPercentage"]
