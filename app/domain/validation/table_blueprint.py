from __future__ import annotations

import re
from typing import Any

from app.domain.validation.form_blueprint import FIELD_ID_PATTERN, validate_form_blueprint
from app.domain.validation.issues import ValidationIssue

OUTPUT_KEY_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def validate_table_blueprint(
    table: dict[str, Any] | None,
    *,
    strict: bool = True,
) -> list[ValidationIssue]:
    if table is None:
        return [
            ValidationIssue(
                code="MISSING_TABLE",
                message="table baseKind requires a table configuration block",
                field="table",
            )
        ]

    issues: list[ValidationIssue] = []
    columns = table.get("columns")
    if not isinstance(columns, list):
        issues.append(
            ValidationIssue(
                code="INVALID_TABLE_COLUMNS",
                message="table.columns must be a list",
                field="table.columns",
            )
        )
        columns = []
    elif strict and not columns:
        issues.append(
            ValidationIssue(
                code="MISSING_TABLE_COLUMNS",
                message="table.columns must be a non-empty list",
                field="table.columns",
            )
        )
    if columns:
        issues.extend(
            validate_form_blueprint(
                {
                    "fields": columns,
                    "crossFieldConstraints": table.get("crossFieldConstraints") or [],
                }
            )
        )
        for index, column in enumerate(columns):
            if isinstance(column, dict):
                field_path = f"table.columns[{index}]"
                issues.extend(_validate_column_field_path(field_path, column))

    output_key = table.get("outputKey")
    if not isinstance(output_key, str) or not output_key:
        issues.append(
            ValidationIssue(
                code="MISSING_OUTPUT_KEY",
                message="table.outputKey is required",
                field="table.outputKey",
            )
        )
    elif not OUTPUT_KEY_PATTERN.match(output_key):
        issues.append(
            ValidationIssue(
                code="INVALID_OUTPUT_KEY",
                message="table.outputKey must be a valid identifier",
                field="table.outputKey",
            )
        )

    column_ids = {
        str(column["id"])
        for column in (columns or [])
        if isinstance(column, dict) and column.get("id")
    }
    if isinstance(output_key, str) and output_key in column_ids:
        issues.append(
            ValidationIssue(
                code="OUTPUT_KEY_COLLISION",
                message=f"table.outputKey '{output_key}' must not match a column id",
                field="table.outputKey",
            )
        )

    min_rows = table.get("minRows", 1)
    if not isinstance(min_rows, int) or isinstance(min_rows, bool) or min_rows < 0:
        issues.append(
            ValidationIssue(
                code="INVALID_MIN_ROWS",
                message="table.minRows must be a non-negative integer",
                field="table.minRows",
            )
        )

    summary = table.get("summary")
    if summary is not None:
        issues.extend(_validate_summary(summary, column_ids, output_key))

    return issues


def _validate_column_field_path(field_path: str, column: dict[str, Any]) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    field_id = column.get("id")
    if not isinstance(field_id, str) or not FIELD_ID_PATTERN.match(field_id):
        return issues

    for key in ("remoteSource", "remoteOptions"):
        config = column.get(key)
        if not isinstance(config, dict):
            continue
        requires = config.get("requires")
        if not isinstance(requires, list):
            continue
        for ref in requires:
            if isinstance(ref, str) and "." in ref:
                issues.append(
                    ValidationIssue(
                        code="INVALID_COLUMN_REFERENCE",
                        message=(
                            f"Column '{field_id}' {key}.requires entries must be "
                            "top-level column ids, not nested paths"
                        ),
                        field=f"{field_path}.{key}.requires",
                        details={"reference": ref},
                    )
                )
    return issues


def _validate_summary(
    summary: Any,
    column_ids: set[str],
    output_key: str | None,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(summary, dict):
        return [
            ValidationIssue(
                code="INVALID_TABLE_SUMMARY",
                message="table.summary must be an object",
                field="table.summary",
            )
        ]

    column_id = summary.get("columnId")
    summary_output_key = summary.get("outputKey")
    if not isinstance(column_id, str) or column_id not in column_ids:
        issues.append(
            ValidationIssue(
                code="UNKNOWN_SUMMARY_COLUMN",
                message="table.summary.columnId must reference a table column id",
                field="table.summary.columnId",
            )
        )
    if not isinstance(summary_output_key, str) or not summary_output_key:
        issues.append(
            ValidationIssue(
                code="MISSING_SUMMARY_OUTPUT_KEY",
                message="table.summary.outputKey is required",
                field="table.summary.outputKey",
            )
        )
    elif not OUTPUT_KEY_PATTERN.match(summary_output_key):
        issues.append(
            ValidationIssue(
                code="INVALID_SUMMARY_OUTPUT_KEY",
                message="table.summary.outputKey must be a valid identifier",
                field="table.summary.outputKey",
            )
        )
    elif summary_output_key == output_key:
        issues.append(
            ValidationIssue(
                code="SUMMARY_OUTPUT_KEY_COLLISION",
                message="table.summary.outputKey must differ from table.outputKey",
                field="table.summary.outputKey",
            )
        )
    elif summary_output_key in column_ids:
        issues.append(
            ValidationIssue(
                code="SUMMARY_OUTPUT_KEY_COLLISION",
                message="table.summary.outputKey must not match a column id",
                field="table.summary.outputKey",
            )
        )

    return issues
