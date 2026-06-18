from app.application.executions.scheduler import GraphScheduler
from app.domain.enums import NodeStatus
from app.domain.graph import WorkflowGraph


def test_ready_task_nodes_after_start():
    graph = WorkflowGraph.from_definition_json(
        {
            "nodes": [
                {"id": "start", "kind": "start", "position": {"x": 0, "y": 0}},
                {
                    "id": "task-1",
                    "kind": "task",
                    "nodeDefinitionId": "n1",
                    "position": {"x": 1, "y": 0},
                },
                {
                    "id": "task-2",
                    "kind": "task",
                    "nodeDefinitionId": "n2",
                    "position": {"x": 2, "y": 0},
                    "inputs": [
                        {
                            "inputKey": "x",
                            "source": {
                                "kind": "upstream",
                                "sourceNodeId": "task-1",
                                "outputKey": "x",
                            },
                        }
                    ],
                },
                {"id": "end", "kind": "end", "position": {"x": 3, "y": 0}},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "task-1"},
                {"id": "e2", "source": "task-1", "target": "task-2"},
                {"id": "e3", "source": "task-2", "target": "end"},
            ],
        }
    )
    scheduler = GraphScheduler(graph)
    statuses = {
        "task-1": NodeStatus.WAITING,
        "task-2": NodeStatus.WAITING,
    }
    ready = scheduler.ready_task_nodes(statuses)
    assert [node.id for node in ready] == ["task-1"]

    statuses["task-1"] = NodeStatus.COMPLETED
    ready = scheduler.ready_task_nodes(statuses)
    assert [node.id for node in ready] == ["task-2"]


def test_all_tasks_completed():
    graph = WorkflowGraph.from_definition_json(
        {
            "nodes": [
                {"id": "start", "kind": "start", "position": {"x": 0, "y": 0}},
                {
                    "id": "task-1",
                    "kind": "task",
                    "nodeDefinitionId": "n1",
                    "position": {"x": 1, "y": 0},
                },
                {"id": "end", "kind": "end", "position": {"x": 2, "y": 0}},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "task-1"},
                {"id": "e2", "source": "task-1", "target": "end"},
            ],
        }
    )
    scheduler = GraphScheduler(graph)
    assert not scheduler.all_tasks_completed({"task-1": NodeStatus.PENDING})
    assert scheduler.all_tasks_completed({"task-1": NodeStatus.COMPLETED})


def test_resolve_next_task_id_from_completed_task():
    graph = WorkflowGraph.from_definition_json(
        {
            "nodes": [
                {"id": "start", "kind": "start"},
                {"id": "task-1", "kind": "task", "nodeDefinitionId": "n1"},
                {"id": "task-2", "kind": "task", "nodeDefinitionId": "n2"},
                {"id": "end", "kind": "end"},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "task-1"},
                {"id": "e2", "source": "task-1", "target": "task-2"},
                {"id": "e3", "source": "task-2", "target": "end"},
            ],
        }
    )
    scheduler = GraphScheduler(graph)
    statuses = {
        "task-1": NodeStatus.COMPLETED,
        "task-2": NodeStatus.PENDING,
    }

    assert scheduler.resolve_next_task_id(statuses, from_node_id="task-1") == "task-2"
    assert scheduler.resolve_next_task_id(statuses, from_node_id="task-2") is None
