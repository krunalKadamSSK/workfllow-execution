from __future__ import annotations

from typing import Any

from app.domain.definitions.table_fields import (
    collect_table_input_field_ids,
    collect_table_output_field_ids,
    declared_table_output,
    table_cost_contribution,
)
from app.domain.validation.issues import ValidationIssue


def _user_input_declared_output(definition_json: dict[str, Any]) -> dict[str, str] | None:
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


def _collect_user_input_output_field_ids(definition_json: dict[str, Any]) -> set[str]:
    field_ids: set[str] = set()
    form = definition_json.get("form") or {}
    for field in form.get("fields") or []:
        if isinstance(field, dict) and "id" in field:
            field_ids.add(str(field["id"]))

    output_decl = _user_input_declared_output(definition_json)
    if output_decl is not None:
        field_ids.add(output_decl["id"])

    return field_ids


def _user_input_cost_contribution(
    definition_json: dict[str, Any], outputs: dict[str, Any]
) -> float | None:
    output_decl = _user_input_declared_output(definition_json)
    if output_decl is None:
        return None

    value = outputs.get(output_decl["id"])
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)


def declared_output(definition_json: dict[str, Any]) -> dict[str, str] | None:
    if definition_json.get("baseKind") == "table":
        return declared_table_output(definition_json)
    return _user_input_declared_output(definition_json)


def _collect_user_input_input_field_ids(definition_json: dict[str, Any]) -> set[str]:
    field_ids: set[str] = set()
    form = definition_json.get("form") or {}
    for field in form.get("fields") or []:
        if isinstance(field, dict) and "id" in field:
            field_ids.add(str(field["id"]))
    return field_ids


def collect_input_field_ids(definition_json: dict[str, Any]) -> set[str]:
    if definition_json.get("baseKind") == "table":
        return collect_table_input_field_ids(definition_json)
    return _collect_user_input_input_field_ids(definition_json)


def collect_output_field_ids(definition_json: dict[str, Any]) -> set[str]:
    if definition_json.get("baseKind") == "table":
        return collect_table_output_field_ids(definition_json)
    return _collect_user_input_output_field_ids(definition_json)


def cost_contribution(definition_json: dict[str, Any], outputs: dict[str, Any]) -> float | None:
    if definition_json.get("baseKind") == "table":
        return table_cost_contribution(definition_json, outputs)
    return _user_input_cost_contribution(definition_json, outputs)


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

    if definition_json.get("baseKind") == "table":
        aggregations = definition_json.get("aggregations") or []
        aggregation = next(
            (row for row in aggregations if isinstance(row, dict) and row.get("id") == output_id),
            None,
        )
        if aggregation is None:
            return [
                ValidationIssue(
                    code="UNKNOWN_OUTPUT_AGGREGATION",
                    message=f"output.id '{output_id}' does not match any aggregation",
                    field="output.id",
                    details={"reference": output_id},
                )
            ]
        operation = aggregation.get("operation")
        if operation not in {"sum", "min", "max", "avg"}:
            return [
                ValidationIssue(
                    code="INVALID_OUTPUT_AGGREGATION_OP",
                    message="output.id must reference a numeric aggregation",
                    field="output.id",
                    details={"operation": operation},
                )
            ]
        return []

    fields = definition_json.get("form", {}).get("fields") or []
    field_by_id: dict[str, dict[str, Any]] = {}
    for field in fields:
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
