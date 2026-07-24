from __future__ import annotations

from typing import Any

from app.application.executions.definition_maps import NodeDefinitionMaps, load_node_definition_maps
from app.domain.definitions.output_fields import declared_output
from app.domain.graph.workflow_graph import WorkflowGraph
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.infrastructure.persistence.models.instances import WorkflowNodeInstance
from app.patterns.executions.helpers.task_names import resolve_task_name


def build_execution_summary(
    *,
    graph: WorkflowGraph,
    workflow_projection: dict[str, Any] | None,
    node_instances: list[WorkflowNodeInstance],
    definition_repository: DefinitionRepository | None = None,
    task_names: dict[str, str] | None = None,
    definition_maps: NodeDefinitionMaps | None = None,
) -> dict[str, Any]:
    """Build per-task cost line items and total from the workflow projection."""
    if workflow_projection is None:
        return {"items": [], "total": None}

    maps = definition_maps
    if maps is None:
        if definition_repository is None:
            raise ValueError("definition_repository or definition_maps is required")
        maps = load_node_definition_maps(
            definition_repository,
            node_instances,
            extra_definition_ids={
                node.node_definition_id
                for node in graph.task_nodes
                if node.node_definition_id is not None
            },
        )

    nodes_state = workflow_projection.get("nodes", {})
    instances_by_graph_id = {node.workflow_node_id: node for node in node_instances}
    items: list[dict[str, Any]] = []

    for graph_node in graph.task_nodes:
        node_state = nodes_state.get(graph_node.id)
        if node_state is None or node_state.get("status") != "COMPLETED":
            continue

        node_instance = instances_by_graph_id.get(graph_node.id)
        if node_instance is None:
            continue

        version = maps.versions_by_id.get(node_instance.node_definition_version_id)
        if version is None:
            continue

        output_decl = declared_output(version.definition_json)
        if output_decl is None:
            continue

        outputs = node_state.get("outputs", {})
        task_name = (task_names or {}).get(graph_node.id)
        if not task_name:
            node_definition = (
                maps.definitions_by_id.get(graph_node.node_definition_id)
                if graph_node.node_definition_id
                else None
            )
            task_name = resolve_task_name(
                graph_node=graph_node,
                definition_json=version.definition_json,
                definition_name=node_definition.name if node_definition else None,
            )
        items.append(
            {
                "workflow_node_id": graph_node.id,
                "node_definition_id": graph_node.node_definition_id,
                "task_name": task_name,
                "task_label": task_name,
                "output_key": output_decl["id"],
                "output_label": output_decl["label"],
                "value": outputs.get(output_decl["id"]),
            }
        )

    return {
        "items": items,
        "total": workflow_projection.get("total"),
    }
