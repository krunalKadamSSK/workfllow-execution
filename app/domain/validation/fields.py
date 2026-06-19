from __future__ import annotations

import re
import uuid
from typing import Any
from urllib.parse import urlparse

from app.domain.exceptions import FieldValidationError

EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
CROSS_FIELD_LOGIC_PATTERN = re.compile(
    r"^([a-zA-Z_][a-zA-Z0-9_.]*)\s*(===|==|!==|!=|<=|>=|<|>)\s*(.+)$"
)
FIELD_ID_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_.]*$")
MAX_REGEX_PATTERN_LENGTH = 200


def _is_empty(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _field_error(field_id: str, rule: str, message: str) -> dict[str, str]:
    return {"field": field_id, "rule": rule, "message": message}


def _resolve_field_path(values: dict[str, Any], path: str) -> Any:
    root_key, _, remainder = path.partition(".")
    current = values.get(root_key)
    if not remainder:
        return current
    for part in remainder.split("."):
        if not isinstance(current, dict):
            return None
        current = current.get(part)
    return current


def _parse_literal(operand: str) -> Any:
    operand = operand.strip()
    if len(operand) >= 2 and operand[0] == operand[-1] and operand[0] in {"'", '"'}:
        return operand[1:-1]
    try:
        if "." in operand:
            return float(operand)
        return int(operand)
    except ValueError:
        return operand


def _normalize_operator(operator: str) -> str:
    if operator == "===":
        return "=="
    if operator == "!==":
        return "!="
    return operator


def _compare(left: Any, operator: str, right: Any) -> bool:
    operator = _normalize_operator(operator)

    if operator == "==":
        return left == right
    if operator == "!=":
        return left != right

    try:
        left_num = float(left)
        right_num = float(right)
    except (TypeError, ValueError):
        return False

    if operator == "<":
        return left_num < right_num
    if operator == "<=":
        return left_num <= right_num
    if operator == ">":
        return left_num > right_num
    if operator == ">=":
        return left_num >= right_num

    return False


class FormFieldValidator:
    """Replay Synapse per-field and cross-field validation rules on submit."""

    def validate_form(
        self,
        fields: list[dict[str, Any]],
        values: dict[str, Any],
        *,
        cross_field_constraints: list[dict[str, Any]] | None = None,
    ) -> None:
        errors: list[dict[str, str]] = []

        for field in fields:
            field_id = str(field["id"])
            value = values.get(field_id)
            for rule in field.get("validation", []):
                error = self._validate_rule(field_id, rule, value)
                if error is not None:
                    errors.append(error)

        if cross_field_constraints:
            errors.extend(self._validate_cross_field_constraints(cross_field_constraints, values))

        if errors:
            raise FieldValidationError(
                "One or more fields failed validation",
                field_errors=errors,
            )

    def _validate_cross_field_constraints(
        self,
        constraints: list[dict[str, Any]],
        values: dict[str, Any],
    ) -> list[dict[str, str]]:
        errors: list[dict[str, str]] = []

        for constraint in constraints:
            logic = str(constraint.get("logic", "")).strip()
            target = str(constraint.get("target", ""))
            message = str(constraint.get("message") or f"Cross-field validation failed for {target}")

            match = CROSS_FIELD_LOGIC_PATTERN.match(logic)
            if match is None:
                errors.append(
                    _field_error(target or "form", "crossField", f"Invalid constraint logic: {logic}")
                )
                continue

            left_ref, operator, right_operand = match.groups()
            left_value = _resolve_field_path(values, left_ref)

            right_operand = right_operand.strip()
            if (
                len(right_operand) >= 2
                and right_operand[0] == right_operand[-1]
                and right_operand[0] in {"'", '"'}
            ):
                right_value = _parse_literal(right_operand)
            elif FIELD_ID_PATTERN.match(right_operand):
                right_value = _resolve_field_path(values, right_operand)
            else:
                right_value = _parse_literal(right_operand)

            if not _compare(left_value, operator, right_value):
                errors.append(_field_error(target, "crossField", message))

        return errors

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

        if rule_name in {"pattern", "regex"}:
            pattern = str(rule.get("value", ""))
            if len(pattern) > MAX_REGEX_PATTERN_LENGTH:
                return _field_error(
                    field_id,
                    str(rule_name),
                    f"Pattern must be at most {MAX_REGEX_PATTERN_LENGTH} characters",
                )
            if not re.fullmatch(pattern, str(value)):
                return _field_error(field_id, str(rule_name), message)
            return None

        if rule_name == "minLength":
            try:
                minimum = int(rule["value"])
                if len(str(value)) < minimum:
                    return _field_error(field_id, "minLength", message)
            except (TypeError, ValueError):
                return _field_error(field_id, "minLength", message)
            return None

        if rule_name == "maxLength":
            try:
                maximum = int(rule["value"])
                if len(str(value)) > maximum:
                    return _field_error(field_id, "maxLength", message)
            except (TypeError, ValueError):
                return _field_error(field_id, "maxLength", message)
            return None

        if rule_name == "email":
            if not EMAIL_PATTERN.fullmatch(str(value)):
                return _field_error(field_id, "email", message)
            return None

        if rule_name == "url":
            parsed = urlparse(str(value))
            if parsed.scheme not in {"http", "https"} or not parsed.netloc:
                return _field_error(field_id, "url", message)
            return None

        if rule_name == "uuid":
            try:
                uuid.UUID(str(value))
            except (TypeError, ValueError, AttributeError):
                return _field_error(field_id, "uuid", message)
            return None

        return _field_error(field_id, str(rule_name), f"Unsupported validation rule: {rule_name}")
