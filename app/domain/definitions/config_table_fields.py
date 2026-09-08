from __future__ import annotations

from typing import Any

from app.domain.definitions.table_fields import (
    TABLE_ROWS_INPUT_KEY,
    build_table_task_outputs,
    declared_table_output,
    table_column_input_key,
    table_cost_contribution,
)


CONFIG_TABLE_KEY = "configTable"


def config_table_section(definition_json: dict[str, Any]) -> dict[str, Any]:
    section = definition_json.get(CONFIG_TABLE_KEY)
    return section if isinstance(section, dict) else {}


def collect_config_table_columns(definition_json: dict[str, Any]) -> list[dict[str, Any]]:
    cfg = config_table_section(definition_json)
    columns: list[dict[str, Any]] = []
    for mapping in cfg.get("columnMappings") or []:
        if not isinstance(mapping, dict):
            continue
        field = mapping.get("field")
        if isinstance(field, dict) and field.get("id"):
            columns.append(field)
    for field in cfg.get("extraColumns") or []:
        if isinstance(field, dict) and field.get("id"):
            columns.append(field)
    return columns


def collect_config_table_extra_columns(
    definition_json: dict[str, Any],
) -> list[dict[str, Any]]:
    cfg = config_table_section(definition_json)
    columns: list[dict[str, Any]] = []
    for field in cfg.get("extraColumns") or []:
        if isinstance(field, dict) and field.get("id"):
            columns.append(field)
    return columns


def collect_config_table_query_inputs(
    definition_json: dict[str, Any],
) -> list[dict[str, Any]]:
    cfg = config_table_section(definition_json)
    inputs: list[dict[str, Any]] = []
    for row in cfg.get("queryInputs") or []:
        if isinstance(row, dict) and row.get("id"):
            inputs.append(row)
    return inputs


def collect_config_table_input_field_ids(definition_json: dict[str, Any]) -> set[str]:
    """Query params + extra columns (column:id) — never From DB mapped fields."""
    field_ids: set[str] = set()
    for row in collect_config_table_query_inputs(definition_json):
        field_ids.add(str(row["id"]))
    for column in collect_config_table_extra_columns(definition_json):
        field_ids.add(table_column_input_key(str(column["id"])))
    field_ids.add(TABLE_ROWS_INPUT_KEY)
    return field_ids


def collect_config_table_output_field_ids(definition_json: dict[str, Any]) -> set[str]:
    field_ids: set[str] = {TABLE_ROWS_INPUT_KEY}
    for column in collect_config_table_columns(definition_json):
        field_ids.add(str(column["id"]))
    for aggregation in definition_json.get("aggregations") or []:
        if isinstance(aggregation, dict) and aggregation.get("id"):
            field_ids.add(str(aggregation["id"]))
    output = declared_table_output(definition_json)
    if output is not None:
        field_ids.add(output["id"])
    return field_ids


def build_config_table_task_outputs(
    query_values: dict[str, Any],
    rows: list[dict[str, Any]],
    aggregations: list[dict[str, Any]],
) -> dict[str, Any]:
    return build_table_task_outputs(query_values, rows, aggregations)


def config_table_cost_contribution(
    definition_json: dict[str, Any], outputs: dict[str, Any]
) -> float | None:
    return table_cost_contribution(definition_json, outputs)


def flatten_row_for_validation(row: dict[str, Any]) -> dict[str, Any]:
    """Drop internal metadata keys before Synapse field validation."""
    return {
        key: value
        for key, value in row.items()
        if not str(key).startswith("_") and key not in {"source", "sourceId"}
    }
