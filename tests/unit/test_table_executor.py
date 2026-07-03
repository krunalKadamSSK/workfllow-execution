import pytest

from app.domain.definitions.table_fields import (
    build_table_task_outputs,
    compute_table_aggregation,
)
from app.domain.executors.table_input import TableExecutor
from app.domain.ports.executors import ExecutionContext


def test_compute_table_aggregation_sum():
    rows = [{"lineTotal": 50}, {"lineTotal": 40}]
    assert compute_table_aggregation(rows, "lineTotal", "sum") == 90.0


def test_table_executor_complete_builds_aggregation_outputs():
    executor = TableExecutor()
    context = ExecutionContext(
        workflow_instance_id="inst-1",
        workflow_node_instance_id="node-inst-1",
        workflow_node_id="node-1",
        node_definition_version_id="ver-1",
        base_kind="table",
        definition_json={
            "baseKind": "table",
            "table": {
                "columns": [
                    {"id": "lineTotal", "type": "number", "label": "Line total"},
                ],
            },
            "aggregations": [
                {
                    "id": "totalChildCost",
                    "label": "Total",
                    "columnId": "lineTotal",
                    "operation": "sum",
                }
            ],
        },
    )

    outputs = executor.run(
        context,
        {
            "rows": [
                {"lineTotal": 10},
                {"lineTotal": 15},
            ]
        },
    )

    assert outputs["totalChildCost"] == 25.0
    assert outputs["rows"] == [{"lineTotal": 10}, {"lineTotal": 15}]


def test_build_table_task_outputs_includes_rows_key():
    outputs = build_table_task_outputs(
        {"customerName": "ACME"},
        [{"lineTotal": 5}],
        [{"id": "totalChildCost", "columnId": "lineTotal", "operation": "sum"}],
    )
    assert outputs["customerName"] == "ACME"
    assert outputs["totalChildCost"] == 5.0
    assert outputs["rows"] == [{"lineTotal": 5}]
