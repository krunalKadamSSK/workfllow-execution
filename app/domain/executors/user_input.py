from __future__ import annotations

from typing import Any

from app.domain.exceptions import FieldValidationError
from app.domain.executors.base import BaseNodeExecutor
from app.domain.executors.formula import FormulaError, evaluate_formula
from app.domain.executors.remote_source import prepare_remote_source
from app.domain.ports.executors import ExecutionContext
from app.domain.validation.fields import FormFieldValidator


class UserInputExecutor(BaseNodeExecutor):
    """Strategy executor for baseKind=userInput form nodes."""

    def __init__(self, field_validator: FormFieldValidator | None = None) -> None:
        self._field_validator = field_validator or FormFieldValidator()

    @property
    def base_kind(self) -> str:
        return "userInput"

    def prepare(self, context: ExecutionContext) -> dict[str, Any]:
        prepared = dict(context.resolved_inputs)
        fields = self._form_fields(context)

        for field in fields:
            remote = prepare_remote_source(field, prepared)
            if remote is not None:
                prepared[f"__remoteSource.{field['id']}"] = remote

        return prepared

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
        clean_outputs = self._strip_internal_keys(outputs)
        self._validate_locked_inputs(context, clean_outputs)
        self._field_validator.validate_form(self._form_fields(context), clean_outputs)

    def complete(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]:
        clean_outputs = self._strip_internal_keys(outputs)
        return self._apply_calculations(self._form_fields(context), clean_outputs)

    def _form_fields(self, context: ExecutionContext) -> list[dict[str, Any]]:
        return context.definition_json.get("form", {}).get("fields", [])

    def _validate_locked_inputs(
        self, context: ExecutionContext, outputs: dict[str, Any]
    ) -> None:
        errors: list[dict[str, str]] = []
        for key in context.locked_input_keys:
            if key not in context.resolved_inputs:
                continue
            expected = context.resolved_inputs[key]
            submitted = outputs.get(key)
            if submitted != expected:
                errors.append(
                    {
                        "field": key,
                        "rule": "locked",
                        "message": f"Field '{key}' is locked to upstream value",
                    }
                )
        if errors:
            raise FieldValidationError(
                "Locked upstream inputs were modified",
                field_errors=errors,
            )

    def _apply_calculations(
        self, fields: list[dict[str, Any]], values: dict[str, Any]
    ) -> dict[str, Any]:
        result = dict(values)
        for _ in range(len(fields)):
            changed = False
            for field in fields:
                calculation = field.get("calculation")
                if not calculation:
                    continue
                field_id = str(field["id"])
                try:
                    computed = evaluate_formula(str(calculation["formula"]), result)
                except FormulaError:
                    continue
                if result.get(field_id) != computed:
                    result[field_id] = computed
                    changed = True
            if not changed:
                break
        return result

    @staticmethod
    def _strip_internal_keys(outputs: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in outputs.items() if not str(key).startswith("__")}
