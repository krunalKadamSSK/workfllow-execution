"""Table-specific publish and submit validation helpers."""

from __future__ import annotations

from typing import Any

from app.domain.definitions.table_fields import (
    TABLE_ROWS_INPUT_KEY,
    parse_table_column_input_key,
)
from app.domain.exceptions import FieldValidationError
from app.domain.ports.execution_context import ExecutionContext
from app.domain.validation.fields import FormFieldValidator
from app.domain.validation.issues import ValidationIssue


def validate_table_declared_output(definition_json: dict[str, Any]) -> list[ValidationIssue]:
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


def validate_table_outputs(
    *,
    context: ExecutionContext,
    outputs: dict[str, Any],
    field_validator: FormFieldValidator,
    validate_locked_inputs,
) -> None:
    definition = context.definition_json
    table = definition.get("table") or {}
    header_fields = table.get("headerFields") or []
    columns = table.get("columns") or []
    cross_field_constraints = table.get("crossFieldConstraints")

    validate_locked_inputs(context, outputs)

    header_values: dict[str, Any] = {}
    for field in header_fields:
        if isinstance(field, dict) and field.get("id"):
            field_id = str(field["id"])
            header_values[field_id] = outputs.get(field_id)

    field_validator.validate_form(
        header_fields,
        header_values,
        cross_field_constraints=None,
    )

    rows = outputs.get(TABLE_ROWS_INPUT_KEY)
    if not isinstance(rows, list):
        raise FieldValidationError(
            "Table rows must be an array",
            field_errors=[
                {
                    "field": TABLE_ROWS_INPUT_KEY,
                    "rule": "array",
                    "message": "Table rows must be an array",
                }
            ],
        )

    min_rows = int(table.get("minRows") or 0)
    max_rows = table.get("maxRows")
    if len(rows) < min_rows:
        raise FieldValidationError(
            f"At least {min_rows} row(s) required",
            field_errors=[
                {
                    "field": TABLE_ROWS_INPUT_KEY,
                    "rule": "minRows",
                    "message": f"At least {min_rows} row(s) required",
                }
            ],
        )
    if isinstance(max_rows, int) and len(rows) > max_rows:
        raise FieldValidationError(
            f"At most {max_rows} row(s) allowed",
            field_errors=[
                {
                    "field": TABLE_ROWS_INPUT_KEY,
                    "rule": "maxRows",
                    "message": f"At most {max_rows} row(s) allowed",
                }
            ],
        )

    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise FieldValidationError(
                f"Row {index + 1} must be an object",
                field_errors=[
                    {
                        "field": TABLE_ROWS_INPUT_KEY,
                        "rule": "object",
                        "message": f"Row {index + 1} must be an object",
                    }
                ],
            )
        field_validator.validate_form(
            columns,
            row,
            cross_field_constraints=cross_field_constraints,
        )

    validate_locked_rows_and_columns(context, outputs)


def validate_locked_rows_and_columns(
    context: ExecutionContext, outputs: dict[str, Any]
) -> None:
    errors: list[dict[str, str]] = []
    resolved = context.resolved_inputs

    if TABLE_ROWS_INPUT_KEY in context.locked_input_keys:
        expected_rows = resolved.get(TABLE_ROWS_INPUT_KEY)
        submitted_rows = outputs.get(TABLE_ROWS_INPUT_KEY)
        if submitted_rows != expected_rows:
            errors.append(
                {
                    "field": TABLE_ROWS_INPUT_KEY,
                    "rule": "locked",
                    "message": "Locked upstream rows were modified",
                }
            )

    rows = outputs.get(TABLE_ROWS_INPUT_KEY)
    row_list = rows if isinstance(rows, list) else []

    for key in context.locked_input_keys:
        column_id = parse_table_column_input_key(key)
        if not column_id or key not in resolved:
            continue
        expected = resolved[key]
        for index, row in enumerate(row_list):
            if not isinstance(row, dict):
                continue
            if row.get(column_id) != expected:
                errors.append(
                    {
                        "field": f"{TABLE_ROWS_INPUT_KEY}[{index}].{column_id}",
                        "rule": "locked",
                        "message": (
                            f"Locked column '{column_id}' was modified in row {index + 1}"
                        ),
                    }
                )

    if errors:
        raise FieldValidationError("Locked upstream inputs were modified", field_errors=errors)
