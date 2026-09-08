from __future__ import annotations

from typing import Any

from app.domain.definitions.config_table_fields import (
    build_config_table_task_outputs,
    collect_config_table_columns,
    collect_config_table_extra_columns,
    collect_config_table_query_inputs,
    config_table_section,
    flatten_row_for_validation,
)
from app.domain.definitions.table_fields import (
    TABLE_ROWS_INPUT_KEY,
    parse_table_column_input_key,
)
from app.domain.exceptions import FieldValidationError
from app.domain.executors.base import BaseNodeExecutor
from app.domain.ports.executors import ExecutionContext
from app.domain.validation.fields import FormFieldValidator


class ConfigTableExecutor(BaseNodeExecutor):
    """Strategy executor for baseKind=configTable tasks.

    Row fetch from the Config API is performed by the frontend in v1.
    This executor validates submitted rows (Synapse fields) and recomputes
    aggregations/output the same way as the table executor.
    """

    def __init__(self, field_validator: FormFieldValidator | None = None) -> None:
        self._field_validator = field_validator or FormFieldValidator()

    @property
    def base_kind(self) -> str:
        return "configTable"

    def prepare_pending_node_form(self, context: ExecutionContext) -> dict[str, Any]:
        definition = context.definition_json
        cfg = config_table_section(definition)
        query_inputs = collect_config_table_query_inputs(definition)
        columns = collect_config_table_columns(definition)
        extra_columns = collect_config_table_extra_columns(definition)
        extra_ids = {
            str(column["id"])
            for column in extra_columns
            if isinstance(column, dict) and column.get("id")
        }
        resolved = {**context.seed_defaults, **context.resolved_inputs}

        enriched_query_inputs: list[dict[str, Any]] = []
        for field in query_inputs:
            next_field = dict(field)
            field_id = str(field.get("id", ""))
            if field_id and field_id in resolved:
                next_field["defaultValue"] = resolved[field_id]
            enriched_query_inputs.append(next_field)

        # Only extra columns accept upstream defaults (never From DB mappings).
        column_defaults: dict[str, Any] = {}
        for key, value in resolved.items():
            column_id = parse_table_column_input_key(str(key))
            if column_id and column_id in extra_ids:
                column_defaults[column_id] = value

        enriched_extra_columns: list[dict[str, Any]] = []
        for field in extra_columns:
            next_field = dict(field)
            field_id = str(field.get("id", ""))
            if field_id in column_defaults:
                next_field["defaultValue"] = column_defaults[field_id]
            enriched_extra_columns.append(next_field)

        # Frontend fills initialRows after Config API fetch; merge any upstream rows.
        initial_rows: list[dict[str, Any]] = []
        raw_rows = resolved.get(TABLE_ROWS_INPUT_KEY)
        if isinstance(raw_rows, list):
            for row in raw_rows:
                if not isinstance(row, dict):
                    continue
                merged = {**column_defaults, **dict(row)}
                initial_rows.append(merged)

        return {
            "formKind": "configTable",
            "aggregations": definition.get("aggregations") or [],
            "configTable": {
                "dataSource": cfg.get("dataSource") or {},
                "queryInputs": enriched_query_inputs,
                "queryFilters": cfg.get("queryFilters") or [],
                "columnMappings": cfg.get("columnMappings") or [],
                "extraColumns": enriched_extra_columns,
                "columns": [dict(column) for column in columns],
                "crossFieldConstraints": cfg.get("crossFieldConstraints"),
                "allowEditFetchedRows": bool(cfg.get("allowEditFetchedRows", False)),
                "allowAddRows": bool(cfg.get("allowAddRows", True)),
                "allowDeleteRows": bool(cfg.get("allowDeleteRows", True)),
                "initialRows": initial_rows,
                "lockedKeys": list(context.locked_input_keys),
                "columnDefaults": column_defaults,
                "minRows": int(cfg.get("minRows") or 0),
                "maxRows": cfg.get("maxRows"),
                "aggregations": definition.get("aggregations") or [],
            },
        }

    def prepare_form_fields(self, context: ExecutionContext) -> list[dict[str, Any]]:
        return []

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
        clean_outputs = self._strip_internal_keys(outputs)
        definition = context.definition_json
        cfg = config_table_section(definition)
        query_inputs = collect_config_table_query_inputs(definition)
        columns = collect_config_table_columns(definition)
        cross_field_constraints = cfg.get("crossFieldConstraints")

        self._validate_locked_inputs(context, clean_outputs)

        query_values: dict[str, Any] = {}
        for field in query_inputs:
            field_id = str(field.get("id", ""))
            if field_id:
                query_values[field_id] = clean_outputs.get(field_id)

        self._field_validator.validate_form(
            query_inputs,
            query_values,
            cross_field_constraints=None,
        )

        rows = clean_outputs.get(TABLE_ROWS_INPUT_KEY)
        if not isinstance(rows, list):
            raise FieldValidationError(
                "Config table rows must be an array",
                field_errors=[
                    {
                        "field": TABLE_ROWS_INPUT_KEY,
                        "rule": "array",
                        "message": "Config table rows must be an array",
                    }
                ],
            )

        min_rows = int(cfg.get("minRows") or 0)
        max_rows = cfg.get("maxRows")
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
                flatten_row_for_validation(row),
                cross_field_constraints=cross_field_constraints,
            )

    def complete(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]:
        clean_outputs = self._strip_internal_keys(outputs)
        definition = context.definition_json
        query_inputs = collect_config_table_query_inputs(definition)
        aggregations = definition.get("aggregations") or []

        query_values: dict[str, Any] = {}
        for field in query_inputs:
            field_id = str(field.get("id", ""))
            if field_id and field_id in clean_outputs:
                query_values[field_id] = clean_outputs[field_id]

        rows = clean_outputs.get(TABLE_ROWS_INPUT_KEY)
        row_list = (
            [dict(row) for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []
        )

        return build_config_table_task_outputs(query_values, row_list, aggregations)
