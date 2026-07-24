from __future__ import annotations

from typing import Any

from app.domain.definitions.table_fields import (
    TABLE_ROWS_INPUT_KEY,
    build_table_task_outputs,
    collect_table_input_field_ids,
    collect_table_output_field_ids,
    declared_table_output,
    parse_table_column_input_key,
    table_cost_contribution,
)
from app.domain.ports.execution_context import ExecutionContext
from app.domain.seed.field_classifier import FieldSeedClassifier, filter_static_outputs
from app.domain.validation.fields import FormFieldValidator
from app.domain.validation.issues import ValidationIssue
from app.patterns.executions.strategies.base import BaseNodeExecutor
from app.patterns.executions.strategies.table_validation import (
    validate_table_declared_output,
    validate_table_outputs,
)


class TableExecutor(BaseNodeExecutor):
    """Strategy for baseKind=table (human table tasks)."""

    def __init__(self, field_validator: FormFieldValidator | None = None) -> None:
        self._field_validator = field_validator or FormFieldValidator()

    @property
    def base_kind(self) -> str:
        return "table"

    def runs_automatically(self) -> bool:
        return False

    def normalize_definition_json(self, definition_json: dict[str, Any]) -> dict[str, Any]:
        payload = dict(definition_json)
        if "table" not in payload:
            payload["table"] = {
                "headerFields": [],
                "columns": [],
                "crossFieldConstraints": [],
                "minRows": None,
                "maxRows": None,
                "defaultRows": None,
            }
        if "aggregations" not in payload:
            payload["aggregations"] = []
        return payload

    def validate_definition(self, definition_json: dict[str, Any]) -> list[ValidationIssue]:
        return validate_table_declared_output(definition_json)

    def extract_seed_defaults(
        self,
        definition_json: dict[str, Any],
        outputs: dict[str, Any],
        *,
        classifier: FieldSeedClassifier,
    ) -> dict[str, Any]:
        table = definition_json.get("table") or {}
        header_fields = table.get("headerFields") or []
        seeded = filter_static_outputs(
            outputs=outputs,
            fields=header_fields if isinstance(header_fields, list) else [],
            classifier=classifier,
        )
        rows = outputs.get(TABLE_ROWS_INPUT_KEY)
        if isinstance(rows, list):
            seeded[TABLE_ROWS_INPUT_KEY] = rows
        return seeded

    def declared_output(self, definition_json: dict[str, Any]) -> dict[str, str] | None:
        return declared_table_output(definition_json)

    def collect_input_field_ids(self, definition_json: dict[str, Any]) -> set[str]:
        return collect_table_input_field_ids(definition_json)

    def collect_output_field_ids(self, definition_json: dict[str, Any]) -> set[str]:
        return collect_table_output_field_ids(definition_json)

    def cost_contribution(
        self, definition_json: dict[str, Any], outputs: dict[str, Any]
    ) -> float | None:
        return table_cost_contribution(definition_json, outputs)

    def prepare_pending_node_form(self, context: ExecutionContext) -> dict[str, Any]:
        definition = context.definition_json
        table = definition.get("table") or {}
        columns = table.get("columns") or []
        header_fields = table.get("headerFields") or []
        resolved = {**context.seed_defaults, **context.resolved_inputs}

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
            initial_rows = [self._create_empty_row(columns, column_defaults) for _ in range(count)]
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
        validate_table_outputs(
            context=context,
            outputs=self._strip_internal_keys(outputs),
            field_validator=self._field_validator,
            validate_locked_inputs=self._validate_locked_inputs,
        )

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
        row_list = (
            [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        )
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
