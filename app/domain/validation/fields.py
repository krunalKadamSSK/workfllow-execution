from __future__ import annotations

import re
from typing import Any

from app.domain.exceptions import FieldValidationError


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _field_error(field_id: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field_id, "rule": rule, "message": message}


class FormFieldValidator:
    """Chain of Responsibility for replaying node form validation rules."""

    def validate_form(self, fields: list[dict[str, Any]], values: dict[str, Any]) -> None:
        errors: list[dict[str, str]] = []

        for field in fields:
            field_id = str(field["id"])
            value = values.get(field_id)
            for rule in field.get("validation", []):
                error = self._validate_rule(field_id, rule, value)
                if error is not None:
                    errors.append(error)

        if errors:
            raise FieldValidationError(
                "One or more fields failed validation",
                field_errors=errors,
            )

    def _validate_rule(
        self,
        field_id: str,
        rule: dict[str, Any],
        value: Any,
    ) -> dict[str, str] | None:
        rule_name = rule.get("rule")
        message = rule.get("message") or f"Validation failed for {field_id}"

        if rule_name == "required":
            if _is_empty(value):
                return _field_error(field_id, "required", message)
            return None

        if _is_empty(value):
            return None

        if rule_name == "min":
            try:
                minimum = float(rule["value"])
                if float(value) < minimum:
                    return _field_error(field_id, "min", message)
            except (TypeError, ValueError):
                return _field_error(field_id, "min", message)
            return None

        if rule_name == "max":
            try:
                maximum = float(rule["value"])
                if float(value) > maximum:
                    return _field_error(field_id, "max", message)
            except (TypeError, ValueError):
                return _field_error(field_id, "max", message)
            return None

        if rule_name == "pattern":
            pattern = str(rule.get("value", ""))
            if not re.fullmatch(pattern, str(value)):
                return _field_error(field_id, "pattern", message)
            return None

        return _field_error(field_id, str(rule_name), f"Unsupported validation rule: {rule_name}")
