from __future__ import annotations

import re
from typing import Any

from app.domain.validation.issues import ValidationIssue

SYNAPSE_FIELD_TYPES = frozenset({"text", "number", "select", "autocomplete"})
FIELD_ID_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")
IDENTIFIER_PATTERN = re.compile(r"[a-zA-Z_][a-zA-Z0-9_.]*")
URL_TEMPLATE_PATTERN = re.compile(r"\{\{([^}]+)\}\}")
CROSS_FIELD_LOGIC_PATTERN = re.compile(
    r"^([a-zA-Z_][a-zA-Z0-9_.]*)\s*(===|==|!==|!=|<=|>=|<|>)\s*(.+)$"
)


def validate_form_blueprint(form: dict[str, Any] | None) -> list[ValidationIssue]:
    """Mirror validateSynapseBlueprint semantic checks on save/publish."""
    if form is None:
        return []

    fields = form.get("fields") or []
    if not isinstance(fields, list):
        return [
            ValidationIssue(
                code="INVALID_FORM_FIELDS",
                message="form.fields must be a list",
                field="form.fields",
            )
        ]

    issues: list[ValidationIssue] = []
    field_ids: list[str] = []
    field_id_set: set[str] = set()

    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            issues.append(
                ValidationIssue(
                    code="INVALID_FORM_FIELD",
                    message="Each form field must be an object",
                    field=f"form.fields[{index}]",
                )
            )
            continue

        field_id = field.get("id")
        if not isinstance(field_id, str) or not field_id:
            issues.append(
                ValidationIssue(
                    code="MISSING_FIELD_ID",
                    message="Form field id is required",
                    field=f"form.fields[{index}].id",
                )
            )
            continue

        field_ids.append(field_id)
        if field_id in field_id_set:
            issues.append(
                ValidationIssue(
                    code="DUPLICATE_FIELD_ID",
                    message=f"Duplicate field id: {field_id}",
                    field=f"form.fields[{index}].id",
                )
            )
        field_id_set.add(field_id)

        field_type = field.get("type")
        if not isinstance(field_type, str) or field_type not in SYNAPSE_FIELD_TYPES:
            issues.append(
                ValidationIssue(
                    code="UNKNOWN_FIELD_TYPE",
                    message=f"Unsupported field type: {field_type!r}",
                    field=f"form.fields[{index}].type",
                    details={"allowed": sorted(SYNAPSE_FIELD_TYPES)},
                )
            )

        calculation = field.get("calculation")
        if isinstance(calculation, dict):
            formula = calculation.get("formula")
            if isinstance(formula, str) and len(formula) > 500:
                issues.append(
                    ValidationIssue(
                        code="FORMULA_TOO_LONG",
                        message="calculation.formula must be at most 500 characters",
                        field=f"form.fields[{index}].calculation.formula",
                    )
                )

    issues.extend(_validate_dangling_references(fields, field_id_set))
    issues.extend(_validate_cross_field_constraints(form, field_id_set))
    return issues


def _validate_dangling_references(
    fields: list[dict[str, Any]],
    field_id_set: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    for index, field in enumerate(fields):
        if not isinstance(field, dict):
            continue

        field_path = f"form.fields[{index}]"
        field_id = str(field.get("id", ""))

        calculation = field.get("calculation")
        if isinstance(calculation, dict):
            formula = calculation.get("formula")
            if isinstance(formula, str):
                for ref in _formula_references(formula):
                    if ref not in field_id_set:
                        issues.append(
                            ValidationIssue(
                                code="DANGLING_FIELD_REFERENCE",
                                message=f"Unknown field reference '{ref}' in calculation.formula",
                                field=f"{field_path}.calculation.formula",
                                details={"reference": ref, "sourceField": field_id},
                            )
                        )

        remote_source = field.get("remoteSource")
        if isinstance(remote_source, dict):
            issues.extend(
                _validate_remote_references(
                    remote_source,
                    field_id_set,
                    f"{field_path}.remoteSource",
                    source_field=field_id,
                )
            )

        remote_options = field.get("remoteOptions")
        if isinstance(remote_options, dict):
            issues.extend(
                _validate_remote_references(
                    remote_options,
                    field_id_set,
                    f"{field_path}.remoteOptions",
                    source_field=field_id,
                )
            )

    return issues


def _validate_remote_references(
    config: dict[str, Any],
    field_id_set: set[str],
    field_path: str,
    *,
    source_field: str,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    url = config.get("url")
    if isinstance(url, str):
        for ref in URL_TEMPLATE_PATTERN.findall(url):
            ref = ref.strip()
            if ref not in field_id_set:
                issues.append(
                    ValidationIssue(
                        code="DANGLING_FIELD_REFERENCE",
                        message=f"Unknown field reference '{ref}' in URL template",
                        field=f"{field_path}.url",
                        details={"reference": ref, "sourceField": source_field},
                    )
                )

    requires = config.get("requires")
    if isinstance(requires, list):
        for ref in requires:
            if not isinstance(ref, str):
                continue
            if ref not in field_id_set:
                issues.append(
                    ValidationIssue(
                        code="DANGLING_FIELD_REFERENCE",
                        message=f"Unknown field reference '{ref}' in requires",
                        field=f"{field_path}.requires",
                        details={"reference": ref, "sourceField": source_field},
                    )
                )

    return issues


def _validate_cross_field_constraints(
    form: dict[str, Any],
    field_id_set: set[str],
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    constraints = form.get("crossFieldConstraints") or []

    if not isinstance(constraints, list):
        return [
            ValidationIssue(
                code="INVALID_CROSS_FIELD_CONSTRAINTS",
                message="crossFieldConstraints must be a list",
                field="form.crossFieldConstraints",
            )
        ]

    for index, constraint in enumerate(constraints):
        if not isinstance(constraint, dict):
            issues.append(
                ValidationIssue(
                    code="INVALID_CROSS_FIELD_CONSTRAINT",
                    message="Each crossFieldConstraint must be an object",
                    field=f"form.crossFieldConstraints[{index}]",
                )
            )
            continue

        field_path = f"form.crossFieldConstraints[{index}]"
        target = constraint.get("target")
        if isinstance(target, str) and target not in field_id_set:
            issues.append(
                ValidationIssue(
                    code="DANGLING_FIELD_REFERENCE",
                    message=f"Unknown target field '{target}'",
                    field=f"{field_path}.target",
                    details={"reference": target},
                )
            )

        logic = constraint.get("logic")
        if not isinstance(logic, str):
            continue

        match = CROSS_FIELD_LOGIC_PATTERN.match(logic.strip())
        if match is None:
            issues.append(
                ValidationIssue(
                    code="INVALID_CROSS_FIELD_LOGIC",
                    message="crossFieldConstraint logic must match '<field> <op> <operand>'",
                    field=f"{field_path}.logic",
                )
            )
            continue

        left_ref, _, right_operand = match.groups()
        if left_ref not in field_id_set:
            issues.append(
                ValidationIssue(
                    code="DANGLING_FIELD_REFERENCE",
                    message=f"Unknown field reference '{left_ref}' in logic",
                    field=f"{field_path}.logic",
                    details={"reference": left_ref},
                )
            )

        right_ref = _cross_field_right_reference(right_operand.strip(), field_id_set)
        if right_ref is not None and right_ref not in field_id_set:
            issues.append(
                ValidationIssue(
                    code="DANGLING_FIELD_REFERENCE",
                    message=f"Unknown field reference '{right_ref}' in logic",
                    field=f"{field_path}.logic",
                    details={"reference": right_ref},
                )
            )

    return issues


def _formula_references(formula: str) -> set[str]:
    return set(IDENTIFIER_PATTERN.findall(formula))


def _cross_field_right_reference(operand: str, field_id_set: set[str]) -> str | None:
    if _is_quoted_literal(operand):
        return None
    if operand in field_id_set:
        return operand
    if FIELD_ID_PATTERN.match(operand):
        return operand
    return None


def _is_quoted_literal(operand: str) -> bool:
    return (
        len(operand) >= 2
        and operand[0] == operand[-1]
        and operand[0] in {"'", '"'}
    )
