from app.domain.validation.graph import validate_graph_topology, validate_node_references
from app.domain.validation.input_wiring import validate_input_wiring
from app.domain.validation.issues import ValidationIssue
from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest


def validate_workflow_definition(
    workflow: WorkflowDefinitionIngest,
    *,
    published_node_ids: set[str],
    node_output_fields: dict[str, set[str]],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    issues.extend(validate_graph_topology(workflow))
    issues.extend(validate_node_references(workflow, published_node_ids=published_node_ids))
    issues.extend(validate_input_wiring(workflow, node_output_fields=node_output_fields))
    return issues
