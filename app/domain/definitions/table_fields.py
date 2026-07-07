from __future__ import annotations

from typing import Any

TABLE_ROWS_INPUT_KEY = "rows"
TABLE_COLUMN_INPUT_PREFIX = "column:"


def table_column_input_key(column_id: str) -> str:
    return f"{TABLE_COLUMN_INPUT_PREFIX}{column_id}"


def parse_table_column_input_key(input_key: str) -> str | None:
    if not input_key.startswith(TABLE_COLUMN_INPUT_PREFIX):
        return None
    column_id = input_key[len(TABLE_COLUMN_INPUT_PREFIX) :]
    return column_id or None


def _parse_numeric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _numeric_values(rows: list[dict[str, Any]], column_id: str) -> list[float]:
    values: list[float] = []
    for row in rows:
        parsed = _parse_numeric(row.get(column_id))
        if parsed is not None:
            values.append(parsed)
    return values


def _count_non_empty(rows: list[dict[str, Any]], column_id: str) -> int:
    count = 0
    for row in rows:
        value = row.get(column_id)
        if value is not None and value != "":
            count += 1
    return count


def compute_table_aggregation(
    rows: list[dict[str, Any]],
    column_id: str,
    operation: str,
) -> float | int | None:
    if operation == "count":
        return _count_non_empty(rows, column_id)

    values = _numeric_values(rows, column_id)
    if not values:
        return None

    if operation == "sum":
        return float(sum(values))
    if operation == "min":
        return float(min(values))
    if operation == "max":
        return float(max(values))
    if operation == "avg":
        return float(sum(values) / len(values))
    return None


def build_table_task_outputs(
    header: dict[str, Any],
    rows: list[dict[str, Any]],
    aggregations: list[dict[str, Any]],
) -> dict[str, Any]:
    outputs: dict[str, Any] = {**header, TABLE_ROWS_INPUT_KEY: rows}
    for aggregation in aggregations:
        aggregation_id = aggregation.get("id")
        column_id = aggregation.get("columnId")
        operation = aggregation.get("operation")
        if not isinstance(aggregation_id, str) or not aggregation_id:
            continue
        if not isinstance(column_id, str) or not column_id:
            continue
        if not isinstance(operation, str) or not operation:
            continue
        outputs[aggregation_id] = compute_table_aggregation(rows, column_id, operation)
    return outputs


def collect_table_input_field_ids(definition_json: dict[str, Any]) -> set[str]:
    field_ids: set[str] = set()
    table = definition_json.get("table") or {}
    for field in table.get("headerFields") or []:
        if isinstance(field, dict) and field.get("id"):
            field_ids.add(str(field["id"]))
    for column in table.get("columns") or []:
        if isinstance(column, dict) and column.get("id"):
            field_ids.add(table_column_input_key(str(column["id"])))
    field_ids.add(TABLE_ROWS_INPUT_KEY)
    return field_ids


def collect_table_output_field_ids(definition_json: dict[str, Any]) -> set[str]:
    field_ids: set[str] = set()
    table = definition_json.get("table") or {}
    for field in table.get("headerFields") or []:
        if isinstance(field, dict) and field.get("id"):
            field_ids.add(str(field["id"]))

    for aggregation in definition_json.get("aggregations") or []:
        if isinstance(aggregation, dict) and aggregation.get("id"):
            field_ids.add(str(aggregation["id"]))

    field_ids.add(TABLE_ROWS_INPUT_KEY)

    output_decl = declared_table_output(definition_json)
    if output_decl is not None:
        field_ids.add(output_decl["id"])

    return field_ids


def declared_table_output(definition_json: dict[str, Any]) -> dict[str, str] | None:
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


def table_cost_contribution(
    definition_json: dict[str, Any], outputs: dict[str, Any]
) -> float | None:
    output_decl = declared_table_output(definition_json)
    if output_decl is None:
        return None

    value = outputs.get(output_decl["id"])
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value)
