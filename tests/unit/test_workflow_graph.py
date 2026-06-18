import json
from pathlib import Path

import pytest

from app.domain.graph import WorkflowGraph

FIXTURES = Path(__file__).parent.parent / "fixtures"


@pytest.fixture
def workflow_graph() -> WorkflowGraph:
    data = json.loads((FIXTURES / "workflow_test.json").read_text())
    stored = {
        "description": data.get("description"),
        "nodes": data["nodes"],
        "edges": data["edges"],
    }
    return WorkflowGraph.from_definition_json(stored)


class TestWorkflowGraph:
    def test_from_definition_json(self, workflow_graph: WorkflowGraph):
        assert len(workflow_graph.nodes) == 4
        assert len(workflow_graph.task_nodes) == 2

    def test_start_and_end_nodes(self, workflow_graph: WorkflowGraph):
        assert workflow_graph.start_node.kind == "start"
        assert len(workflow_graph.end_nodes) == 1

    def test_successors_and_predecessors(self, workflow_graph: WorkflowGraph):
        start_id = workflow_graph.start_node.id
        successors = workflow_graph.successors(start_id)
        assert len(successors) == 1

        task_id = successors[0]
        assert workflow_graph.predecessors(task_id) == (start_id,)

    def test_downstream_task_nodes(self, workflow_graph: WorkflowGraph):
        first_task = workflow_graph.successors(workflow_graph.start_node.id)[0]
        downstream = workflow_graph.downstream_task_nodes(first_task)
        assert len(downstream) == 1
        assert downstream[0].node_definition_id == "220b5a4f-de75-45ef-b3bb-8f7f794e301e"

    def test_topological_order(self, workflow_graph: WorkflowGraph):
        order = workflow_graph.topological_order()
        assert order[0] == workflow_graph.start_node.id
        assert order[-1] == workflow_graph.end_nodes[0].id

    def test_task_node_input_bindings(self, workflow_graph: WorkflowGraph):
        pricing_task = workflow_graph.task_nodes[1]
        assert len(pricing_task.inputs) == 2
        assert pricing_task.inputs[0].output_key == "customerName"

    def test_missing_node_raises(self, workflow_graph: WorkflowGraph):
        with pytest.raises(KeyError):
            workflow_graph.require_node("missing")
