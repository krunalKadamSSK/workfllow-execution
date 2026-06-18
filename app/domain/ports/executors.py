from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class ExecutionContext:
    workflow_instance_id: str
    workflow_node_instance_id: str
    workflow_node_id: str
    node_definition_version_id: str
    base_kind: str
    definition_json: dict[str, Any]
    resolved_inputs: dict[str, Any] = field(default_factory=dict)
    execution_number: int = 0


@runtime_checkable
class NodeExecutor(Protocol):
    """Strategy interface for executing a workflow node kind."""

    @property
    def base_kind(self) -> str: ...

    def prepare(self, context: ExecutionContext) -> dict[str, Any]:
        """Build default outputs or prefilled values before user/system action."""

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
        """Validate submitted or computed outputs."""

    def complete(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]:
        """Finalize outputs after validation."""


@runtime_checkable
class InputResolver(Protocol):
    """Resolves upstream node outputs into task input values."""

    def resolve(
        self,
        *,
        workflow_instance_id: str,
        source_node_id: str,
        output_key: str,
    ) -> Any: ...


@runtime_checkable
class FieldValidator(Protocol):
    """Validates a single form field value against node definition rules."""

    def validate(
        self,
        *,
        field_id: str,
        field_definition: dict[str, Any],
        value: Any,
    ) -> None: ...
