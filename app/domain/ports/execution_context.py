"""Shared execution context value object for node executors."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class ExecutionContext:
    workflow_instance_id: str
    workflow_node_instance_id: str
    workflow_node_id: str
    node_definition_version_id: str
    base_kind: str
    definition_json: dict[str, Any]
    resolved_inputs: dict[str, Any] = field(default_factory=dict)
    locked_input_keys: frozenset[str] = field(default_factory=frozenset)
    execution_number: int = 0
    seed_defaults: dict[str, Any] = field(default_factory=dict)
