from __future__ import annotations

from typing import Any

from app.domain.definitions.table_fields import (
    TABLE_COLUMN_INPUT_PREFIX,
    TABLE_ROWS_INPUT_KEY,
    build_table_task_outputs,
    parse_table_column_input_key,
    table_column_input_key,
)
from app.domain.exceptions import FieldValidationError
from app.domain.executors.base import BaseNodeExecutor
from app.domain.ports.executors import ExecutionContext
from app.domain.validation.fields import FormFieldValidator


class TableExecutor(BaseNodeExecutor):
    """Strategy executor for baseKind=table tasks."""

    def __init__(self, field_validator: FormFieldValidator | None = None) -> None:
        self._field_validator = field_validator or FormFieldValidator()

    @property
    def base_kind(self) -> str:
        return "table"

    def prepare_pending_node_form(self, context: ExecutionContext) -> dict[str, Any]:
        definition = context.definition_json
        table = definition.get("table") or {}
        columns = table.get("columns") or []
        header_fields = table.get("headerFields") or []
        resolved = context.resolved_inputs

        column_defaults: dict[str, Any] = {}
        for key, value in resolved.items():
            column_id = parse_table_column_input_key(str(key))
            if column_id:
                column_defaults[column_id] = value

        raw_rows = resolved.get(TABLE_ROWS_INPUT_KEY)
        initial_rows = (
            [dict(row) for row in raw_rows if isinstance(row, dict)]
            if isinstance(raw_rows, list)
            else []
        )

        min_rows = int(table.get("minRows") or 1)
        default_rows = int(table.get("defaultRows") or 1)
        if not initial_rows:
            count = max(default_rows, min_rows)
            initial_rows = [
                self._create_empty_row(columns, column_defaults) for _ in range(count)
            ]
        else:
            initial_rows = [
                {
                    **self._create_empty_row(columns, column_defaults),
                    **row,
                }
                for row in initial_rows
            ]

        return {
            "formKind": "table",
            "aggregations": definition.get("aggregations") or [],
            "table": {
                "headerFields": self._enrich_fields(header_fields, resolved),
                "columns": [dict(column) for column in columns],
                "crossFieldConstraints": table.get("crossFieldConstraints"),
                "initialRows": initial_rows,
                "lockedKeys": list(context.locked_input_keys),
                "columnDefaults": column_defaults,
                "minRows": min_rows,
                "maxRows": table.get("maxRows"),
                "aggregations": definition.get("aggregations") or [],
            },
        }

    def prepare_form_fields(self, context: ExecutionContext) -> list[dict[str, Any]]:
        return []

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
        clean_outputs = self._strip_internal_keys(outputs)
        definition = context.definition_json
        table = definition.get("table") or {}
        header_fields = table.get("headerFields") or []
        columns = table.get("columns") or []
        cross_field_constraints = table.get("crossFieldConstraints")

        self._validate_locked_inputs(context, clean_outputs)

        header_values: dict[str, Any] = {}
        for field in header_fields:
            if isinstance(field, dict) and field.get("id"):
                field_id = str(field["id"])
                header_values[field_id] = clean_outputs.get(field_id)

        self._field_validator.validate_form(
            header_fields,
            header_values,
            cross_field_constraints=None,
        )

        rows = clean_outputs.get(TABLE_ROWS_INPUT_KEY)
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
            self._field_validator.validate_form(
                columns,
                row,
                cross_field_constraints=cross_field_constraints,
            )

        self._validate_locked_rows_and_columns(context, clean_outputs)

    def complete(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]:
        clean_outputs = self._strip_internal_keys(outputs)
        definition = context.definition_json
        table = definition.get("table") or {}
        header_fields = table.get("headerFields") or []
        aggregations = definition.get("aggregations") or []

        header: dict[str, Any] = {}
        for field in header_fields:
            if isinstance(field, dict) and field.get("id"):
                field_id = str(field["id"])
                if field_id in clean_outputs:
                    header[field_id] = clean_outputs[field_id]

        rows = clean_outputs.get(TABLE_ROWS_INPUT_KEY)
        row_list = [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []

        return build_table_task_outputs(header, row_list, aggregations)

    @staticmethod
    def _enrich_fields(
        fields: list[dict[str, Any]],
        resolved: dict[str, Any],
    ) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for field in fields:
            if not isinstance(field, dict):
                continue
            next_field = dict(field)
            field_id = str(field.get("id", ""))
            if field_id and field_id in resolved:
                next_field["defaultValue"] = resolved[field_id]
            enriched.append(next_field)
        return enriched

    @staticmethod
    def _create_empty_row(
        columns: list[dict[str, Any]],
        column_defaults: dict[str, Any],
    ) -> dict[str, Any]:
        row: dict[str, Any] = {}
        for column in columns:
            if not isinstance(column, dict) or not column.get("id"):
                continue
            column_id = str(column["id"])
            if column_id in column_defaults:
                row[column_id] = column_defaults[column_id]
            elif "defaultValue" in column:
                row[column_id] = column["defaultValue"]
            else:
                row[column_id] = ""
        return row

    def _validate_locked_rows_and_columns(
        self, context: ExecutionContext, outputs: dict[str, Any]
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
                            "message": f"Locked column '{column_id}' was modified in row {index + 1}",
                        }
                    )

        if errors:
            raise FieldValidationError("Locked upstream inputs were modified", field_errors=errors)
