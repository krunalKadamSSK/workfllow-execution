from __future__ import annotations

from typing import Any

from app.domain.graph.workflow_graph import GraphNode, WorkflowGraph
from app.infrastructure.db.models.instances import WorkflowNodeInstance
from app.infrastructure.db.repositories.definitions import DefinitionRepository


def resolve_task_name(
    *,
    graph_node: GraphNode,
    definition_json: dict[str, Any] | None = None,
) -> str:
    """Return a human-readable task name for display in the UI."""
    if graph_node.label:
        return graph_node.label
    if definition_json is not None:
        name = definition_json.get("name")
        if isinstance(name, str) and name:
            return name
    return graph_node.id


def build_task_names(
    *,
    graph: WorkflowGraph,
    node_instances: list[WorkflowNodeInstance],
    definition_repository: DefinitionRepository,
) -> dict[str, str]:
    """Map workflow graph node ids to display names for all tasks."""
    instances_by_graph_id = {node.workflow_node_id: node for node in node_instances}
    names: dict[str, str] = {}

    for graph_node in graph.task_nodes:
        definition_json: dict[str, Any] | None = None
        node_instance = instances_by_graph_id.get(graph_node.id)
        if node_instance is not None:
            version = definition_repository.get_node_definition_version_by_id(
                node_instance.node_definition_version_id
            )
            if version is not None:
                definition_json = version.definition_json

        names[graph_node.id] = resolve_task_name(
            graph_node=graph_node,
            definition_json=definition_json,
        )

    return names
