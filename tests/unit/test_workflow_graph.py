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

    def test_next_pending_task_follows_outgoing_edge(self):
        from app.domain.enums import NodeStatus

        graph = WorkflowGraph.from_definition_json(
            {
                "nodes": [
                    {"id": "start", "kind": "start"},
                    {"id": "task-a", "kind": "task", "nodeDefinitionId": "n1"},
                    {"id": "task-b", "kind": "task", "nodeDefinitionId": "n2"},
                    {"id": "task-c", "kind": "task", "nodeDefinitionId": "n3"},
                    {"id": "end", "kind": "end"},
                ],
                "edges": [
                    {"id": "e1", "source": "start", "target": "task-a"},
                    {"id": "e2", "source": "task-a", "target": "task-b"},
                    {"id": "e3", "source": "task-a", "target": "task-c"},
                    {"id": "e4", "source": "task-b", "target": "end"},
                    {"id": "e5", "source": "task-c", "target": "end"},
                ],
            }
        )

        next_task = graph.next_pending_task_from(
            "task-a",
            {
                "task-a": NodeStatus.COMPLETED,
                "task-b": NodeStatus.PENDING,
                "task-c": NodeStatus.WAITING,
            },
        )
        assert next_task is not None
        assert next_task.id == "task-b"

    def test_next_pending_task_from_start(self):
        from app.domain.enums import NodeStatus

        graph = WorkflowGraph.from_definition_json(
            {
                "nodes": [
                    {"id": "start", "kind": "start"},
                    {"id": "task-1", "kind": "task", "nodeDefinitionId": "n1"},
                    {"id": "end", "kind": "end"},
                ],
                "edges": [
                    {"id": "e1", "source": "start", "target": "task-1"},
                    {"id": "e2", "source": "task-1", "target": "end"},
                ],
            }
        )

        next_task = graph.next_pending_task_from(
            "start",
            {"task-1": NodeStatus.PENDING},
        )
        assert next_task is not None
        assert next_task.id == "task-1"

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
