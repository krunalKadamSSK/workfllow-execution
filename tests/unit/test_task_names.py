from app.application.executions.task_names import build_task_names, resolve_task_name
from app.domain.graph.workflow_graph import GraphNode


def test_resolve_task_name_prefers_graph_label():
    node = GraphNode(
        id="node-1",
        kind="task",
        node_definition_id="def-1",
        label="Custom label",
    )
    assert resolve_task_name(graph_node=node, definition_json={"name": "Definition name"}) == "Custom label"


def test_resolve_task_name_falls_back_to_definition_name():
    node = GraphNode(id="node-1", kind="task", node_definition_id="def-1")
    assert resolve_task_name(graph_node=node, definition_json={"name": "Raw Material Pricing"}) == "Raw Material Pricing"


def test_resolve_task_name_falls_back_to_graph_node_id():
    node = GraphNode(id="node-1", kind="task", node_definition_id="def-1")
    assert resolve_task_name(graph_node=node) == "node-1"


def test_resolve_task_name_uses_workflow_node_name_field():
    node = GraphNode(
        id="node-1",
        kind="task",
        node_definition_id="def-1",
        label="Step 1 - Intake",
    )
    assert resolve_task_name(graph_node=node) == "Step 1 - Intake"


class _Version:
    def __init__(self, definition_json: dict):
        self.definition_json = definition_json


class _NodeInstance:
    def __init__(self, workflow_node_id: str, version_id: str):
        self.workflow_node_id = workflow_node_id
        self.node_definition_version_id = version_id


class _DefinitionRepository:
    def __init__(self, versions: dict[str, dict]):
        self._versions = versions

    def get_node_definition_version_by_id(self, version_id: str):
        payload = self._versions.get(version_id)
        return _Version(payload) if payload is not None else None


def test_build_task_names_maps_all_tasks():
    from app.domain.graph.workflow_graph import WorkflowGraph

    graph = WorkflowGraph.from_definition_json(
        {
            "nodes": [
                {"id": "start", "kind": "start"},
                {
                    "id": "task-1",
                    "kind": "task",
                    "nodeDefinitionId": "def-1",
                },
                {"id": "end", "kind": "end"},
            ],
            "edges": [
                {"id": "e1", "source": "start", "target": "task-1"},
                {"id": "e2", "source": "task-1", "target": "end"},
            ],
        }
    )
    repo = _DefinitionRepository({"ver-1": {"name": "Raw Material Pricing"}})
    names = build_task_names(
        graph=graph,
        node_instances=[_NodeInstance("task-1", "ver-1")],
        definition_repository=repo,
    )
    assert names == {"task-1": "Raw Material Pricing"}
