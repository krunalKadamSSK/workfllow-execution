from __future__ import annotations

from typing import Any

from app.domain.exceptions import FieldValidationError
from app.domain.executors.base import BaseNodeExecutor
from app.domain.ports.executors import ExecutionContext
from app.domain.validation.fields import FormFieldValidator

SUMMARY_TOLERANCE = 1e-6


class TableExecutor(BaseNodeExecutor):
    """Strategy executor for baseKind=table dynamic row collection nodes."""

    def __init__(self, field_validator: FormFieldValidator | None = None) -> None:
        self._field_validator = field_validator or FormFieldValidator()

    @property
    def base_kind(self) -> str:
        return "table"

    def _table_config(self, context: ExecutionContext) -> dict[str, Any]:
        table = context.definition_json.get("table")
        if not isinstance(table, dict):
            raise FieldValidationError("Table configuration is missing")
        return table

    def _columns(self, context: ExecutionContext) -> list[dict[str, Any]]:
        table = self._table_config(context)
        columns = table.get("columns") or []
        return [column for column in columns if isinstance(column, dict)]

    def prepare_pending_form(
        self,
        context: ExecutionContext,
        *,
        initial_rows: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        table = self._table_config(context)
        columns = self._enrich_columns(context)
        payload: dict[str, Any] = {
            "columns": columns,
            "outputKey": table["outputKey"],
            "minRows": table.get("minRows", 1),
            "initialRows": list(initial_rows or []),
        }
        summary = table.get("summary")
        if isinstance(summary, dict):
            payload["summary"] = dict(summary)
        return payload

    def _enrich_columns(self, context: ExecutionContext) -> list[dict[str, Any]]:
        enriched: list[dict[str, Any]] = []
        for column in self._columns(context):
            field = dict(column)
            field_id = str(field["id"])
            if field_id in context.resolved_inputs:
                field["defaultValue"] = context.resolved_inputs[field_id]
            enriched.append(field)
        return enriched

    def prepare(self, context: ExecutionContext) -> dict[str, Any]:
        return {}

    def prepare_form_fields(self, context: ExecutionContext) -> list[dict[str, Any]]:
        return []

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
        table = self._table_config(context)
        output_key = str(table["outputKey"])
        columns = self._columns(context)
        cross_field_constraints = table.get("crossFieldConstraints") or []

        rows = outputs.get(output_key)
        if not isinstance(rows, list):
            raise FieldValidationError(
                f"Output '{output_key}' must be an array of row objects",
                field_errors=[
                    {
                        "field": output_key,
                        "rule": "array",
                        "message": f"Output '{output_key}' must be an array",
                    }
                ],
            )

        min_rows = table.get("minRows", 1)
        if not isinstance(min_rows, int) or isinstance(min_rows, bool):
            min_rows = 1
        if len(rows) < min_rows:
            raise FieldValidationError(
                f"At least {min_rows} row(s) required",
                field_errors=[
                    {
                        "field": output_key,
                        "rule": "minRows",
                        "message": f"At least {min_rows} row(s) required",
                    }
                ],
            )

        errors: list[dict[str, str]] = []
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                errors.append(
                    {
                        "field": f"{output_key}[{index}]",
                        "rule": "object",
                        "message": "Each row must be an object",
                    }
                )
                continue

            try:
                self._field_validator.validate_form(
                    columns,
                    row,
                    cross_field_constraints=cross_field_constraints,
                )
            except FieldValidationError as exc:
                for field_error in exc.details:
                    field = field_error.get("field", "")
                    errors.append(
                        {
                            "field": f"{output_key}[{index}].{field}",
                            "rule": field_error.get("rule", "validation"),
                            "message": field_error.get("message", "Validation failed"),
                        }
                    )

        summary = table.get("summary")
        if isinstance(summary, dict):
            errors.extend(self._validate_summary(outputs, rows, summary, output_key))

        if errors:
            raise FieldValidationError("Table row validation failed", field_errors=errors)

    def _validate_summary(
        self,
        outputs: dict[str, Any],
        rows: list[dict[str, Any]],
        summary: dict[str, Any],
        output_key: str,
    ) -> list[dict[str, str]]:
        summary_output_key = str(summary["outputKey"])
        column_id = str(summary["columnId"])
        submitted_total = outputs.get(summary_output_key)
        if submitted_total is None:
            return [
                {
                    "field": summary_output_key,
                    "rule": "required",
                    "message": f"Summary output '{summary_output_key}' is required",
                }
            ]
        if isinstance(submitted_total, bool) or not isinstance(submitted_total, (int, float)):
            return [
                {
                    "field": summary_output_key,
                    "rule": "number",
                    "message": f"Summary output '{summary_output_key}' must be a number",
                }
            ]

        expected_total = 0.0
        for index, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            value = row.get(column_id)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return [
                    {
                        "field": f"{output_key}[{index}].{column_id}",
                        "rule": "number",
                        "message": f"Summary column '{column_id}' must be numeric in every row",
                    }
                ]
            expected_total += float(value)

        if abs(expected_total - float(submitted_total)) > SUMMARY_TOLERANCE:
            return [
                {
                    "field": summary_output_key,
                    "rule": "summaryMismatch",
                    "message": (
                        f"Summary output '{summary_output_key}' does not match "
                        f"the sum of column '{column_id}'"
                    ),
                }
            ]
        return []

    def complete(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]:
        table = self._table_config(context)
        output_key = str(table["outputKey"])
        cleaned_rows = self._clean_rows(outputs.get(output_key), self._columns(context))
        result: dict[str, Any] = {output_key: cleaned_rows}

        summary = table.get("summary")
        if isinstance(summary, dict):
            summary_output_key = str(summary["outputKey"])
            if summary_output_key in outputs:
                result[summary_output_key] = outputs[summary_output_key]

        return result

    @staticmethod
    def _clean_rows(
        rows: Any,
        columns: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        if not isinstance(rows, list):
            return []
        column_ids = [str(column["id"]) for column in columns]
        cleaned: list[dict[str, Any]] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            cleaned.append({column_id: row.get(column_id) for column_id in column_ids})
        return cleaned
