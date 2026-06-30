import pytest

from app.domain.definitions.output_fields import (
    collect_output_field_ids,
    cost_contribution,
    table_summary_output,
)
from app.domain.exceptions import FieldValidationError
from app.domain.executors.table import TableExecutor
from app.domain.ports.executors import ExecutionContext
from app.domain.validation.table_blueprint import validate_table_blueprint


TABLE_DEFINITION = {
    "baseKind": "table",
    "table": {
        "columns": [
            {
                "id": "partNo",
                "type": "text",
                "label": "Part number",
                "validation": [{"rule": "required", "message": "required"}],
            },
            {
                "id": "qty",
                "type": "number",
                "label": "Qty",
                "validation": [
                    {"rule": "required", "message": "required"},
                    {"rule": "min", "value": 1, "message": "min 1"},
                ],
            },
            {
                "id": "lineCost",
                "type": "number",
                "label": "Line cost",
            },
        ],
        "outputKey": "childParts",
        "summary": {
            "columnId": "lineCost",
            "outputKey": "childPartsTotal",
            "label": "Child parts total",
        },
        "minRows": 1,
    },
}


def _context(**overrides) -> ExecutionContext:
    defaults = {
        "workflow_instance_id": "inst-1",
        "workflow_node_instance_id": "node-inst-1",
        "workflow_node_id": "graph-node-1",
        "node_definition_version_id": "ver-1",
        "base_kind": "table",
        "definition_json": TABLE_DEFINITION,
        "resolved_inputs": {},
        "locked_input_keys": frozenset(),
        "execution_number": 1,
    }
    defaults.update(overrides)
    return ExecutionContext(**defaults)


def test_validate_table_blueprint_passes_for_valid_definition():
    issues = validate_table_blueprint(TABLE_DEFINITION["table"])
    assert issues == []


def test_validate_table_blueprint_requires_columns_and_output_key():
    issues = validate_table_blueprint({})
    codes = {issue.code for issue in issues}
    assert "INVALID_TABLE_COLUMNS" in codes
    assert "MISSING_OUTPUT_KEY" in codes


def test_collect_output_field_ids_includes_table_keys():
    assert collect_output_field_ids(TABLE_DEFINITION) == {
        "partNo",
        "qty",
        "lineCost",
        "childParts",
        "childPartsTotal",
    }


def test_table_summary_output_returns_summary_key():
    assert table_summary_output(TABLE_DEFINITION) == {
        "id": "childPartsTotal",
        "label": "Child parts total",
    }


def test_cost_contribution_uses_table_summary():
    assert cost_contribution(TABLE_DEFINITION, {"childPartsTotal": 70}) == 70.0


def test_prepare_pending_form_returns_table_shape():
    executor = TableExecutor()
    payload = executor.prepare_pending_form(_context(resolved_inputs={"partNo": "PART-1"}))
    assert payload["outputKey"] == "childParts"
    assert payload["minRows"] == 1
    assert payload["initialRows"] == []
    assert payload["summary"]["outputKey"] == "childPartsTotal"
    assert payload["columns"][0]["defaultValue"] == "PART-1"


def test_validate_outputs_rejects_too_few_rows():
    executor = TableExecutor()
    with pytest.raises(FieldValidationError, match="At least 1 row"):
        executor.validate_outputs(_context(), {"childParts": []})


def test_validate_outputs_rejects_summary_mismatch():
    executor = TableExecutor()
    with pytest.raises(FieldValidationError) as exc_info:
        executor.run(
            _context(),
            {
                "childParts": [
                    {"partNo": "A", "qty": 2, "lineCost": 20},
                    {"partNo": "B", "qty": 1, "lineCost": 50},
                ],
                "childPartsTotal": 60,
            },
        )
    assert any(error.get("rule") == "summaryMismatch" for error in exc_info.value.details)


def test_run_accepts_valid_table_submit():
    executor = TableExecutor()
    outputs = executor.run(
        _context(),
        {
            "childParts": [
                {"partNo": "A", "qty": 2, "lineCost": 20, "extra": "ignored"},
                {"partNo": "B", "qty": 1, "lineCost": 50},
            ],
            "childPartsTotal": 70,
        },
    )
    assert outputs == {
        "childParts": [
            {"partNo": "A", "qty": 2, "lineCost": 20},
            {"partNo": "B", "qty": 1, "lineCost": 50},
        ],
        "childPartsTotal": 70,
    }
