from collections import defaultdict, deque

from app.domain.validation.issues import ValidationIssue
from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest

# Product-permanent keys always allowed for metadata bindings.
# currentTotal is runtime-maintained (not collected on Select RFQ).
SYSTEM_METADATA_KEYS = frozenset(
    {"rfqId", "estimateRevision", "estimatedBy", "runName", "currentTotal"}
)


def _ancestors_by_node(workflow: WorkflowDefinitionIngest) -> dict[str, set[str]]:
    """Map each node id to every ancestor reachable by walking edges backwards."""
    incoming: dict[str, list[str]] = defaultdict(list)
    for edge in workflow.edges:
        incoming[edge.target].append(edge.source)

    ancestors: dict[str, set[str]] = {}
    for node in workflow.nodes:
        seen: set[str] = set()
        queue: deque[str] = deque(incoming.get(node.id, []))
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            queue.extend(incoming.get(current, []))
        ancestors[node.id] = seen
    return ancestors


def _allowed_metadata_keys(workflow: WorkflowDefinitionIngest) -> set[str]:
    return set(SYSTEM_METADATA_KEYS) | workflow.metadata_field_keys()


def validate_input_wiring(
    workflow: WorkflowDefinitionIngest,
    *,
    node_output_fields: dict[str, set[str]],
    node_input_fields: dict[str, set[str]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    nodes_by_id = {node.id: node for node in workflow.nodes}
    ancestors_by_node = _ancestors_by_node(workflow)
    allowed_metadata = _allowed_metadata_keys(workflow)

    for node in workflow.task_nodes():
        if not node.inputs:
            continue

        ancestors = ancestors_by_node.get(node.id, set())

        for node_input in node.inputs:
            source = node_input.source
            task_field_ids = node_input_fields.get(node.nodeDefinitionId or "", set())
            if node_input.inputKey not in task_field_ids:
                issues.append(
                    ValidationIssue(
                        code="UNKNOWN_INPUT_KEY",
                        message=(
                            f"Input key '{node_input.inputKey}' is not defined on node "
                            f"definition '{node.nodeDefinitionId}'"
                        ),
                        field="nodes",
                        details={
                            "workflow_node_id": node.id,
                            "input_key": node_input.inputKey,
                            "node_definition_id": node.nodeDefinitionId,
                        },
                    )
                )

            if source.kind == "metadata":
                key = source.key.strip() if source.key else ""
                if not key:
                    issues.append(
                        ValidationIssue(
                            code="EMPTY_METADATA_KEY",
                            message=(
                                f"Input '{node_input.inputKey}' on node '{node.id}' "
                                f"has an empty metadata key"
                            ),
                            field="nodes",
                            details={
                                "workflow_node_id": node.id,
                                "input_key": node_input.inputKey,
                            },
                        )
                    )
                elif key not in allowed_metadata:
                    issues.append(
                        ValidationIssue(
                            code="UNKNOWN_METADATA_KEY",
                            message=(
                                f"Input '{node_input.inputKey}' on node '{node.id}' "
                                f"references unknown metadata key '{key}'"
                            ),
                            field="nodes",
                            details={
                                "workflow_node_id": node.id,
                                "input_key": node_input.inputKey,
                                "metadata_key": key,
                            },
                        )
                    )
                continue

            if source.kind != "upstream":
                issues.append(
                    ValidationIssue(
                        code="UNSUPPORTED_INPUT_SOURCE",
                        message=(
                            f"Unsupported input source kind '{source.kind}' on node '{node.id}'"
                        ),
                        field="nodes",
                        details={"workflow_node_id": node.id, "input_key": node_input.inputKey},
                    )
                )
                continue

            source_node = nodes_by_id.get(source.sourceNodeId)
            if source_node is None:
                issues.append(
                    ValidationIssue(
                        code="INVALID_UPSTREAM_NODE",
                        message=(
                            f"Input '{node_input.inputKey}' on node '{node.id}' references "
                            f"unknown upstream node '{source.sourceNodeId}'"
                        ),
                        field="nodes",
                        details={
                            "workflow_node_id": node.id,
                            "input_key": node_input.inputKey,
                            "source_node_id": source.sourceNodeId,
                        },
                    )
                )
                continue

            if source_node.kind != "task":
                issues.append(
                    ValidationIssue(
                        code="INVALID_UPSTREAM_NODE_KIND",
                        message=(
                            f"Input '{node_input.inputKey}' on node '{node.id}' must reference "
                            f"a task node, not '{source_node.kind}'"
                        ),
                        field="nodes",
                        details={
                            "workflow_node_id": node.id,
                            "source_node_id": source.sourceNodeId,
                            "source_kind": source_node.kind,
                        },
                    )
                )
                continue

            if source.sourceNodeId not in ancestors:
                issues.append(
                    ValidationIssue(
                        code="UPSTREAM_NOT_ANCESTOR",
                        message=(
                            f"Input '{node_input.inputKey}' on node '{node.id}' references "
                            f"upstream '{source.sourceNodeId}' which is not on a path before "
                            f"this task"
                        ),
                        field="nodes",
                        details={
                            "workflow_node_id": node.id,
                            "input_key": node_input.inputKey,
                            "source_node_id": source.sourceNodeId,
                        },
                    )
                )
                continue

            assert source_node.nodeDefinitionId is not None
            output_fields = node_output_fields.get(source_node.nodeDefinitionId, set())
            if source.outputKey not in output_fields:
                issues.append(
                    ValidationIssue(
                        code="UNKNOWN_OUTPUT_KEY",
                        message=(
                            f"Input '{node_input.inputKey}' on node '{node.id}' references "
                            f"unknown output '{source.outputKey}' from upstream node "
                            f"'{source.sourceNodeId}'"
                        ),
                        field="nodes",
                        details={
                            "workflow_node_id": node.id,
                            "input_key": node_input.inputKey,
                            "source_node_id": source.sourceNodeId,
                            "output_key": source.outputKey,
                            "node_definition_id": source_node.nodeDefinitionId,
                        },
                    )
                )

    return issues
