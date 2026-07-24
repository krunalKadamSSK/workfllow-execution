"""Unit tests for automatic task-type strategies and registry dispatch."""

from __future__ import annotations

from typing import Any

from app.domain.ports.execution_context import ExecutionContext
from app.domain.seed.field_classifier import StaticFieldClassifier
from app.domain.validation.issues import ValidationIssue
from app.patterns.executions.factories.registry import NodeExecutorRegistry, create_default_registry
from app.patterns.executions.strategies.base import BaseNodeExecutor


class _EchoAutoExecutor(BaseNodeExecutor):
    """Minimal automatic strategy used only in unit tests."""

    @property
    def base_kind(self) -> str:
        return "echoAuto"

    def runs_automatically(self) -> bool:
        return True

    def validate_definition(self, definition_json: dict[str, Any]) -> list[ValidationIssue]:
        if definition_json.get("echo") is not True:
            return [
                ValidationIssue(
                    code="MISSING_ECHO",
                    message="echo must be true",
                    field="echo",
                )
            ]
        return []

    def on_ready(self, context: ExecutionContext) -> dict[str, Any]:
        return {"echoed": context.resolved_inputs.get("value", "ok")}

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
        return None

    def complete(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]:
        return outputs


def test_human_kinds_do_not_run_automatically():
    registry = create_default_registry()
    assert registry.get("userInput").runs_automatically() is False
    assert registry.get("table").runs_automatically() is False


def test_registry_dispatches_validate_and_seed_without_kind_ifs():
    registry = NodeExecutorRegistry()
    registry.register(_EchoAutoExecutor())
    definition = {"baseKind": "echoAuto", "echo": True}

    assert registry.for_definition(definition).validate_definition(definition) == []
    assert registry.for_definition({"baseKind": "echoAuto"}).validate_definition(
        {"baseKind": "echoAuto"}
    )[0].code == "MISSING_ECHO"

    seeded = registry.for_definition(definition).extract_seed_defaults(
        definition,
        {"unused": 1},
        classifier=StaticFieldClassifier(),
    )
    assert seeded == {}


def test_auto_strategy_on_ready_feeds_run():
    executor = _EchoAutoExecutor()
    context = ExecutionContext(
        workflow_instance_id="wf",
        workflow_node_instance_id="ni",
        workflow_node_id="n1",
        node_definition_version_id="ndv",
        base_kind="echoAuto",
        definition_json={"baseKind": "echoAuto", "echo": True},
        resolved_inputs={"value": "hello"},
    )
    outputs = executor.run(context, executor.on_ready(context))
    assert outputs["echoed"] == "hello"
