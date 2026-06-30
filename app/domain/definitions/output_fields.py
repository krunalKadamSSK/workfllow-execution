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


def table_summary_output(definition_json: dict[str, Any]) -> dict[str, str] | None:
    """Return the table summary output key and label when configured."""
    if definition_json.get("baseKind") != "table":
        return None
    table = definition_json.get("table")
    if not isinstance(table, dict):
        return None
    summary = table.get("summary")
    if not isinstance(summary, dict):
        return None
    output_id = summary.get("outputKey")
    if not isinstance(output_id, str) or not output_id:
        return None
    label = summary.get("label")
    return {
        "id": output_id,
        "label": label if isinstance(label, str) and label else output_id,
    }


def collect_output_field_ids(definition_json: dict[str, Any]) -> set[str]:
    """Collect output keys and field ids exposed for workflow input wiring."""
    if definition_json.get("baseKind") == "table":
        return _collect_table_output_field_ids(definition_json)

    field_ids: set[str] = set()
    form = definition_json.get("form") or {}
    for field in form.get("fields") or []:
        if isinstance(field, dict) and "id" in field:
            field_ids.add(str(field["id"]))

    output_decl = declared_output(definition_json)
    if output_decl is not None:
        field_ids.add(output_decl["id"])

    return field_ids


def _collect_table_output_field_ids(definition_json: dict[str, Any]) -> set[str]:
    field_ids: set[str] = set()
    table = definition_json.get("table") or {}
    for column in table.get("columns") or []:
        if isinstance(column, dict) and column.get("id"):
            field_ids.add(str(column["id"]))
    output_key = table.get("outputKey")
    if isinstance(output_key, str) and output_key:
        field_ids.add(output_key)
    summary = table.get("summary")
    if isinstance(summary, dict):
        summary_output_key = summary.get("outputKey")
        if isinstance(summary_output_key, str) and summary_output_key:
            field_ids.add(summary_output_key)
    return field_ids


def cost_contribution(definition_json: dict[str, Any], outputs: dict[str, Any]) -> float | None:
    """Extract the numeric cost contribution from completed task outputs."""
    summary_decl = table_summary_output(definition_json)
    if summary_decl is not None:
        value = outputs.get(summary_decl["id"])
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    output_decl = declared_output(definition_json)
    if output_decl is None:
        return None

    value = outputs.get(output_decl["id"])
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def validate_declared_output(definition_json: dict[str, Any]) -> list[ValidationIssue]:
    """Validate the optional output declaration on a node definition."""
    if definition_json.get("baseKind") == "table":
        return []

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
