from __future__ import annotations

from typing import Any

from app.domain.validation.issues import ValidationIssue
from app.patterns.executions.factories.registry import get_default_registry


def _strategy(definition_json: dict[str, Any]):
    return get_default_registry().for_definition(definition_json)


def declared_output(definition_json: dict[str, Any]) -> dict[str, str] | None:
    return _strategy(definition_json).declared_output(definition_json)


def collect_input_field_ids(definition_json: dict[str, Any]) -> set[str]:
    return _strategy(definition_json).collect_input_field_ids(definition_json)


def collect_output_field_ids(definition_json: dict[str, Any]) -> set[str]:
    return _strategy(definition_json).collect_output_field_ids(definition_json)


def cost_contribution(definition_json: dict[str, Any], outputs: dict[str, Any]) -> float | None:
    return _strategy(definition_json).cost_contribution(definition_json, outputs)


def validate_declared_output(definition_json: dict[str, Any]) -> list[ValidationIssue]:
    """Validate task-type definition (form/table shape + optional declared output)."""
    return _strategy(definition_json).validate_definition(definition_json)
