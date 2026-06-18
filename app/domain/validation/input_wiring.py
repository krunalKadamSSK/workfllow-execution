from app.domain.validation.issues import ValidationIssue
from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest


def validate_input_wiring(
    workflow: WorkflowDefinitionIngest,
    *,
    node_output_fields: dict[str, set[str]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    nodes_by_id = {node.id: node for node in workflow.nodes}

    for node in workflow.task_nodes():
        if not node.inputs:
            continue

        for node_input in node.inputs:
            source = node_input.source
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

            task_field_ids = node_output_fields.get(node.nodeDefinitionId or "", set())
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

    return issues
