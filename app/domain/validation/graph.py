from collections import deque

from app.domain.validation.issues import ValidationIssue
from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest


def validate_graph_topology(workflow: WorkflowDefinitionIngest) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    nodes_by_id = {node.id: node for node in workflow.nodes}
    node_ids = set(nodes_by_id)

    if not workflow.nodes:
        issues.append(
            ValidationIssue(
                code="EMPTY_GRAPH",
                message="Workflow must contain at least one node",
                field="nodes",
            )
        )
        return issues

    for edge in workflow.edges:
        if edge.source not in node_ids:
            issues.append(
                ValidationIssue(
                    code="INVALID_EDGE",
                    message=f"Edge source '{edge.source}' does not reference a node",
                    field="edges",
                    details={"edge_id": edge.id, "source": edge.source},
                )
            )
        if edge.target not in node_ids:
            issues.append(
                ValidationIssue(
                    code="INVALID_EDGE",
                    message=f"Edge target '{edge.target}' does not reference a node",
                    field="edges",
                    details={"edge_id": edge.id, "target": edge.target},
                )
            )

    start_nodes = [node for node in workflow.nodes if node.kind == "start"]
    end_nodes = [node for node in workflow.nodes if node.kind == "end"]

    if len(start_nodes) != 1:
        issues.append(
            ValidationIssue(
                code="INVALID_START_NODE",
                message="Workflow must contain exactly one start node",
                field="nodes",
                details={"count": len(start_nodes)},
            )
        )

    if not end_nodes:
        issues.append(
            ValidationIssue(
                code="MISSING_END_NODE",
                message="Workflow must contain at least one end node",
                field="nodes",
            )
        )

    adjacency: dict[str, list[str]] = {node_id: [] for node_id in node_ids}
    for edge in workflow.edges:
        if edge.source in adjacency:
            adjacency[edge.source].append(edge.target)

    if len(start_nodes) == 1:
        start_id = start_nodes[0].id
        reachable = _reachable_from(start_id, adjacency)
        unreachable = node_ids - reachable
        if unreachable:
            issues.append(
                ValidationIssue(
                    code="UNREACHABLE_NODES",
                    message="All nodes must be reachable from the start node",
                    field="nodes",
                    details={"node_ids": sorted(unreachable)},
                )
            )

        if end_nodes:
            unreachable_ends = [node.id for node in end_nodes if node.id not in reachable]
            if unreachable_ends:
                issues.append(
                    ValidationIssue(
                        code="UNREACHABLE_END_NODE",
                        message="End nodes must be reachable from the start node",
                        field="nodes",
                        details={"node_ids": unreachable_ends},
                    )
                )

    cycle_nodes = _find_cycle_nodes(adjacency)
    if cycle_nodes:
        issues.append(
            ValidationIssue(
                code="CYCLIC_GRAPH",
                message="Workflow graph must be acyclic",
                field="edges",
                details={"node_ids": sorted(cycle_nodes)},
            )
        )

    return issues


def _reachable_from(start_id: str, adjacency: dict[str, list[str]]) -> set[str]:
    visited: set[str] = set()
    queue = deque([start_id])

    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(adjacency.get(current, []))

    return visited


def _find_cycle_nodes(adjacency: dict[str, list[str]]) -> set[str]:
    visited: set[str] = set()
    stack: set[str] = set()
    cycle_nodes: set[str] = set()

    def visit(node_id: str) -> bool:
        visited.add(node_id)
        stack.add(node_id)

        for neighbor in adjacency.get(node_id, []):
            if neighbor not in visited:
                if visit(neighbor):
                    cycle_nodes.add(node_id)
                    return True
            elif neighbor in stack:
                cycle_nodes.add(node_id)
                cycle_nodes.add(neighbor)
                return True

        stack.remove(node_id)
        return False

    for node_id in adjacency:
        if node_id not in visited and visit(node_id):
            continue

    return cycle_nodes


def validate_node_references(
    workflow: WorkflowDefinitionIngest,
    *,
    published_node_ids: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for node in workflow.task_nodes():
        assert node.nodeDefinitionId is not None
        if node.nodeDefinitionId not in published_node_ids:
            issues.append(
                ValidationIssue(
                    code="UNKNOWN_NODE_DEFINITION",
                    message=(
                        f"Task node '{node.id}' references unknown or unpublished "
                        f"node definition '{node.nodeDefinitionId}'"
                    ),
                    field="nodes",
                    details={
                        "workflow_node_id": node.id,
                        "node_definition_id": node.nodeDefinitionId,
                    },
                )
            )

    return issues
