from unittest.mock import MagicMock

from app.application.executions.summary import build_execution_summary
from app.domain.graph.workflow_graph import GraphNode, WorkflowGraph
from app.infrastructure.db.models.instances import WorkflowNodeInstance


def _node_instance(graph_node_id: str, version_id: str) -> WorkflowNodeInstance:
    return WorkflowNodeInstance(
        id=f"instance-{graph_node_id}",
        workflow_instance_id="wf-1",
        workflow_node_id=graph_node_id,
        node_definition_version_id=version_id,
        status="COMPLETED",
        current_execution=1,
    )


def test_build_execution_summary_uses_node_definition_name_when_json_has_no_name():
    graph = WorkflowGraph(
        nodes=(
            GraphNode(
                id="task-1",
                kind="task",
                node_definition_id="def-1",
            ),
        ),
        edges=(),
    )
    node_instance = _node_instance("task-1", "version-1")
    definition_repository = MagicMock()
    definition_repository.get_node_definition_version_by_id.return_value = MagicMock(
        definition_json={
            "baseKind": "userInput",
            "output": {"id": "lineTotal", "label": "Line total"},
        }
    )
    node_definition = MagicMock()
    node_definition.name = "Raw Material Price"
    definition_repository.get_node_definition.return_value = node_definition

    summary = build_execution_summary(
        graph=graph,
        workflow_projection={
            "nodes": {
                "task-1": {
                    "status": "COMPLETED",
                    "outputs": {"lineTotal": 45.63},
                }
            },
            "total": 45.63,
        },
        node_instances=[node_instance],
        definition_repository=definition_repository,
    )

    assert summary["items"] == [
        {
            "workflow_node_id": "task-1",
            "node_definition_id": "def-1",
            "task_name": "Raw Material Price",
            "task_label": "Raw Material Price",
            "output_key": "lineTotal",
            "output_label": "Line total",
            "value": 45.63,
        }
    ]
