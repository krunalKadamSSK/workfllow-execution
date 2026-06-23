from __future__ import annotations

from typing import Any

from app.application.executions.task_names import resolve_task_name
from app.domain.definitions.output_fields import declared_output
from app.domain.graph.workflow_graph import WorkflowGraph
from app.infrastructure.db.models.instances import WorkflowNodeInstance
from app.infrastructure.db.repositories.definitions import DefinitionRepository


def build_execution_summary(
    *,
    graph: WorkflowGraph,
    workflow_projection: dict[str, Any] | None,
    node_instances: list[WorkflowNodeInstance],
    definition_repository: DefinitionRepository,
    task_names: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Build per-task cost line items and total from the workflow projection."""
    if workflow_projection is None:
        return {"items": [], "total": None}

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

        version = definition_repository.get_node_definition_version_by_id(
            node_instance.node_definition_version_id
        )
        if version is None:
            continue

        output_decl = declared_output(version.definition_json)
        if output_decl is None:
            continue

        outputs = node_state.get("outputs", {})
        task_name = (task_names or {}).get(graph_node.id)
        if not task_name:
            node_definition = (
                definition_repository.get_node_definition(graph_node.node_definition_id)
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
