import pytest

from app.domain.exceptions import FieldValidationError
from app.domain.executors.base import BaseNodeExecutor
from app.domain.ports.executors import ExecutionContext


class EchoExecutor(BaseNodeExecutor):
    @property
    def base_kind(self) -> str:
        return "echo"

    def validate_outputs(self, context: ExecutionContext, outputs: dict) -> None:
        if "required" not in outputs:
            raise FieldValidationError("missing required", field_errors=[{"field": "required"}])


def test_base_executor_template_method_merges_inputs():
    executor = EchoExecutor()
    context = ExecutionContext(
        workflow_instance_id="inst",
        workflow_node_instance_id="node-inst",
        workflow_node_id="node",
        node_definition_version_id="ver",
        base_kind="echo",
        definition_json={},
        resolved_inputs={"prefilled": "yes"},
    )

    result = executor.run(context, {"required": "ok"})
    assert result == {"prefilled": "yes", "required": "ok"}


def test_base_executor_prefers_upstream_over_seed_defaults():
    executor = EchoExecutor()
    context = ExecutionContext(
        workflow_instance_id="inst",
        workflow_node_instance_id="node-inst",
        workflow_node_id="node",
        node_definition_version_id="ver",
        base_kind="echo",
        definition_json={
            "form": {
                "fields": [
                    {"id": "customerName", "type": "text"},
                    {"id": "partName", "type": "text"},
                ]
            }
        },
        resolved_inputs={"customerName": "FROM_UPSTREAM"},
        seed_defaults={"customerName": "FROM_SEED", "partName": "PART-SEED"},
    )

    fields = {field["id"]: field for field in executor.prepare_form_fields(context)}
    assert fields["customerName"]["defaultValue"] == "FROM_UPSTREAM"
    assert fields["partName"]["defaultValue"] == "PART-SEED"

    result = executor.run(context, {"required": "ok"})
    assert result["customerName"] == "FROM_UPSTREAM"
    assert result["partName"] == "PART-SEED"
    assert result["required"] == "ok"


def test_base_executor_propagates_field_validation_error():
    executor = EchoExecutor()
    context = ExecutionContext(
        workflow_instance_id="inst",
        workflow_node_instance_id="node-inst",
        workflow_node_id="node",
        node_definition_version_id="ver",
        base_kind="echo",
        definition_json={},
    )

    with pytest.raises(FieldValidationError):
        executor.run(context, {})
