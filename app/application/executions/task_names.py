from __future__ import annotations

from typing import Any

from app.application.executions.definition_maps import NodeDefinitionMaps
from app.domain.graph.workflow_graph import GraphNode, WorkflowGraph
from app.infrastructure.db.models.instances import WorkflowNodeInstance
from app.infrastructure.db.repositories.definitions import DefinitionRepository


def resolve_task_name(
    *,
    graph_node: GraphNode,
    definition_json: dict[str, Any] | None = None,
    definition_name: str | None = None,
) -> str:
    """Return a human-readable task name for display in the UI."""
    if graph_node.label:
        return graph_node.label
    if definition_json is not None:
        name = definition_json.get("name")
        if isinstance(name, str) and name:
            return name
    if definition_name:
        return definition_name
    return graph_node.id


def build_task_names(
    *,
    graph: WorkflowGraph,
    node_instances: list[WorkflowNodeInstance],
    definition_repository: DefinitionRepository | None = None,
    definition_maps: NodeDefinitionMaps | None = None,
) -> dict[str, str]:
    """Map workflow graph node ids to display names for all tasks."""
    maps = definition_maps
    if maps is None:
        if definition_repository is None:
            raise ValueError("definition_repository or definition_maps is required")
        from app.application.executions.definition_maps import load_node_definition_maps

        maps = load_node_definition_maps(
            definition_repository,
            node_instances,
            extra_definition_ids={
                node.node_definition_id
                for node in graph.task_nodes
                if node.node_definition_id is not None
            },
        )

    instances_by_graph_id = {node.workflow_node_id: node for node in node_instances}
    names: dict[str, str] = {}

    for graph_node in graph.task_nodes:
        definition_json: dict[str, Any] | None = None
        node_instance = instances_by_graph_id.get(graph_node.id)
        if node_instance is not None:
            version = maps.versions_by_id.get(node_instance.node_definition_version_id)
            if version is not None:
                definition_json = version.definition_json

        definition_name = None
        if graph_node.node_definition_id:
            node_definition = maps.definitions_by_id.get(graph_node.node_definition_id)
            if node_definition is not None:
                definition_name = node_definition.name

        names[graph_node.id] = resolve_task_name(
            graph_node=graph_node,
            definition_json=definition_json,
            definition_name=definition_name,
        )

    return names
