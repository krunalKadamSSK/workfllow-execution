from app.application.executions.task_names import build_task_names, resolve_task_name
from app.domain.graph.workflow_graph import GraphNode


def test_resolve_task_name_prefers_graph_label():
    node = GraphNode(
        id="node-1",
        kind="task",
        node_definition_id="def-1",
        label="Custom label",
    )
    assert (
        resolve_task_name(graph_node=node, definition_json={"name": "Definition name"})
        == "Custom label"
    )


def test_resolve_task_name_falls_back_to_definition_name():
    node = GraphNode(id="node-1", kind="task", node_definition_id="def-1")
    assert (
        resolve_task_name(graph_node=node, definition_json={"name": "Raw Material Pricing"})
        == "Raw Material Pricing"
    )


def test_resolve_task_name_falls_back_to_graph_node_id():
    node = GraphNode(id="node-1", kind="task", node_definition_id="def-1")
    assert resolve_task_name(graph_node=node) == "node-1"


def test_resolve_task_name_falls_back_to_node_definition_name():
    node = GraphNode(id="node-1", kind="task", node_definition_id="def-1")
    assert (
        resolve_task_name(graph_node=node, definition_name="Raw Material Pricing")
        == "Raw Material Pricing"
    )


def test_resolve_task_name_uses_workflow_node_name_field():
    node = GraphNode(
        id="node-1",
        kind="task",
        node_definition_id="def-1",
        label="Step 1 - Intake",
    )
    assert resolve_task_name(graph_node=node) == "Step 1 - Intake"


class _Version:
    def __init__(self, *, node_definition_id: str, definition_json: dict):
        self.id = "ver"
        self.node_definition_id = node_definition_id
        self.definition_json = definition_json


class _NodeInstance:
    def __init__(self, workflow_node_id: str, version_id: str):
        self.workflow_node_id = workflow_node_id
        self.node_definition_version_id = version_id


class _NodeDefinition:
    def __init__(self, name: str):
        self.name = name


class _DefinitionRepository:
    def __init__(
        self,
        versions: dict[str, _Version],
        definitions: dict[str, str] | None = None,
    ):
        self._versions = versions
        self._definitions = definitions or {}

    def get_node_definition_versions_by_ids(self, version_ids):
        return {
            version_id: self._versions[version_id]
            for version_id in version_ids
            if version_id in self._versions
        }

    def get_node_definitions_by_ids(self, definition_ids):
        result = {}
        for definition_id in definition_ids:
            name = self._definitions.get(definition_id)
            if name is not None:
                result[definition_id] = _NodeDefinition(name)
        return result


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
    repo = _DefinitionRepository(
        {
            "ver-1": _Version(
                node_definition_id="def-1",
                definition_json={"baseKind": "userInput"},
            )
        },
        definitions={"def-1": "Raw Material Pricing"},
    )
    names = build_task_names(
        graph=graph,
        node_instances=[_NodeInstance("task-1", "ver-1")],
        definition_repository=repo,
    )
    assert names == {"task-1": "Raw Material Pricing"}
