from __future__ import annotations

from app.domain.definitions.config_table_fields import (
    collect_config_table_input_field_ids,
)
from app.domain.executors.config_table_input import ConfigTableExecutor
from app.domain.executors.registry import create_default_registry
from app.domain.ports.executors import ExecutionContext


def _definition() -> dict:
    return {
        "baseKind": "configTable",
        "configTable": {
            "dataSource": {"collection": "customer_cost_master"},
            "queryInputs": [
                {
                    "id": "customerName",
                    "type": "text",
                    "label": "Customer",
                }
            ],
            "queryFilters": [
                {
                    "filterField": "customerName",
                    "filterOperator": "eq",
                    "fieldId": "customerName",
                }
            ],
            "columnMappings": [
                {
                    "dbField": "costItemName",
                    "field": {
                        "id": "costItemName",
                        "type": "text",
                        "label": "Cost item",
                    },
                }
            ],
            "extraColumns": [
                {"id": "qty", "type": "number", "label": "Qty"},
            ],
            "allowEditFetchedRows": False,
            "allowAddRows": True,
            "allowDeleteRows": True,
            "minRows": 0,
        },
        "aggregations": [
            {
                "id": "totalQty",
                "label": "Total qty",
                "columnId": "qty",
                "operation": "sum",
            }
        ],
        "output": {"id": "totalQty", "label": "Total qty"},
    }


def _context(definition: dict | None = None, **kwargs) -> ExecutionContext:
    return ExecutionContext(
        workflow_instance_id="inst-1",
        workflow_node_instance_id="node-inst-1",
        workflow_node_id="node-1",
        node_definition_version_id="ver-1",
        base_kind="configTable",
        definition_json=definition or _definition(),
        resolved_inputs=kwargs.get("resolved_inputs", {}),
        locked_input_keys=kwargs.get("locked_input_keys", frozenset()),
        seed_defaults=kwargs.get("seed_defaults", {}),
    )


def test_registry_includes_config_table() -> None:
    registry = create_default_registry()
    assert "configTable" in registry.registered_kinds()
    assert registry.get("configTable").base_kind == "configTable"


def test_input_field_ids_include_query_and_extra_not_db() -> None:
    field_ids = collect_config_table_input_field_ids(_definition())
    assert "customerName" in field_ids
    assert "column:qty" in field_ids
    assert "rows" in field_ids
    assert "costItemName" not in field_ids
    assert "column:costItemName" not in field_ids


def test_prepare_pending_form_shape() -> None:
    executor = ConfigTableExecutor()
    pending = executor.prepare_pending_node_form(
        _context(
            resolved_inputs={
                "customerName": "Acme",
                "column:qty": 7,
            }
        )
    )
    assert pending["formKind"] == "configTable"
    cfg = pending["configTable"]
    assert cfg["dataSource"]["collection"] == "customer_cost_master"
    assert cfg["queryInputs"][0]["defaultValue"] == "Acme"
    assert cfg["queryFilters"][0]["fieldId"] == "customerName"
    assert cfg["columnDefaults"]["qty"] == 7
    assert cfg["extraColumns"][0]["defaultValue"] == 7
    assert len(cfg["columns"]) == 2
    assert cfg["allowAddRows"] is True


def test_complete_recomputes_aggregations() -> None:
    executor = ConfigTableExecutor()
    outputs = executor.complete(
        _context(),
        {
            "customerName": "Acme",
            "rows": [
                {"costItemName": "A", "qty": 2, "source": "fetched"},
                {"costItemName": "B", "qty": 3, "source": "manual"},
            ],
        },
    )
    assert outputs["totalQty"] == 5.0
    assert len(outputs["rows"]) == 2
