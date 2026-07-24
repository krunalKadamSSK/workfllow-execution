"""Port: node executor strategy."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from app.domain.ports.execution_context import ExecutionContext
from app.domain.seed.field_classifier import FieldSeedClassifier
from app.domain.validation.issues import ValidationIssue


@runtime_checkable
class NodeExecutor(Protocol):
    """Strategy interface for one workflow node ``baseKind``."""

    @property
    def base_kind(self) -> str: ...

    def runs_automatically(self) -> bool: ...

    def normalize_definition_json(self, definition_json: dict[str, Any]) -> dict[str, Any]: ...

    def validate_definition(self, definition_json: dict[str, Any]) -> list[ValidationIssue]: ...

    def extract_seed_defaults(
        self,
        definition_json: dict[str, Any],
        outputs: dict[str, Any],
        *,
        classifier: FieldSeedClassifier,
    ) -> dict[str, Any]: ...

    def declared_output(self, definition_json: dict[str, Any]) -> dict[str, str] | None: ...

    def collect_input_field_ids(self, definition_json: dict[str, Any]) -> set[str]: ...

    def collect_output_field_ids(self, definition_json: dict[str, Any]) -> set[str]: ...

    def cost_contribution(
        self, definition_json: dict[str, Any], outputs: dict[str, Any]
    ) -> float | None: ...

    def prepare(self, context: ExecutionContext) -> dict[str, Any]: ...

    def prepare_form_fields(self, context: ExecutionContext) -> list[dict[str, Any]]: ...

    def prepare_pending_node_form(self, context: ExecutionContext) -> dict[str, Any]: ...

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None: ...

    def complete(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]: ...

    def run(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]: ...

    def on_ready(self, context: ExecutionContext) -> dict[str, Any]: ...
