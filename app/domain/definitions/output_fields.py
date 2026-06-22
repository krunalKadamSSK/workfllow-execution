from __future__ import annotations

from typing import Any

from app.domain.validation.issues import ValidationIssue


def declared_output(definition_json: dict[str, Any]) -> dict[str, str] | None:
    """Return the node's declared cost output key and label, if configured."""
    output = definition_json.get("output")
    if not isinstance(output, dict):
        return None
    output_id = output.get("id")
    if not isinstance(output_id, str) or not output_id:
        return None
    label = output.get("label")
    return {
        "id": output_id,
        "label": label if isinstance(label, str) and label else output_id,
    }


def collect_output_field_ids(definition_json: dict[str, Any]) -> set[str]:
    """Collect form field ids plus any declared output id for workflow validation."""
    field_ids: set[str] = set()
    form = definition_json.get("form") or {}
    for field in form.get("fields") or []:
        if isinstance(field, dict) and "id" in field:
            field_ids.add(str(field["id"]))

    output_decl = declared_output(definition_json)
    if output_decl is not None:
        field_ids.add(output_decl["id"])

    return field_ids


def cost_contribution(definition_json: dict[str, Any], outputs: dict[str, Any]) -> float | None:
    """Extract the numeric cost contribution from completed task outputs."""
    output_decl = declared_output(definition_json)
    if output_decl is None:
        return None

    value = outputs.get(output_decl["id"])
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def validate_declared_output(definition_json: dict[str, Any]) -> list[ValidationIssue]:
    """Validate the optional output declaration on a node definition."""
    output = definition_json.get("output")
    if output is None:
        return []
    if not isinstance(output, dict):
        return [
            ValidationIssue(
                code="INVALID_OUTPUT",
                message="output must be an object",
                field="output",
            )
        ]

    output_id = output.get("id")
    if not isinstance(output_id, str) or not output_id:
        return [
            ValidationIssue(
                code="MISSING_OUTPUT_ID",
                message="output.id is required",
                field="output.id",
            )
        ]

    fields = definition_json.get("form", {}).get("fields") or []
    field_by_id: dict[str, dict[str, Any]] = {}
    for index, field in enumerate(fields):
        if isinstance(field, dict) and field.get("id"):
            field_by_id[str(field["id"])] = field

    referenced = field_by_id.get(output_id)
    if referenced is None:
        return [
            ValidationIssue(
                code="UNKNOWN_OUTPUT_FIELD",
                message=f"output.id '{output_id}' does not match any form field",
                field="output.id",
                details={"reference": output_id},
            )
        ]

    if referenced.get("type") != "number":
        return [
            ValidationIssue(
                code="INVALID_OUTPUT_FIELD_TYPE",
                message="output.id must reference a number form field",
                field="output.id",
                details={"fieldType": referenced.get("type")},
            )
        ]

    return []
