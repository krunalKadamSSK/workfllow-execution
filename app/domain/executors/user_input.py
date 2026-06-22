from __future__ import annotations

from typing import Any

from app.domain.definitions.output_fields import declared_output
from app.domain.exceptions import FieldValidationError
from app.domain.executors.base import BaseNodeExecutor
from app.domain.ports.executors import ExecutionContext
from app.domain.validation.fields import FormFieldValidator


class UserInputExecutor(BaseNodeExecutor):
    """Strategy executor for baseKind=userInput form nodes."""

    def __init__(self, field_validator: FormFieldValidator | None = None) -> None:
        self._field_validator = field_validator or FormFieldValidator()

    @property
    def base_kind(self) -> str:
        return "userInput"

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
        clean_outputs = self._strip_internal_keys(outputs)
        self._validate_locked_inputs(context, clean_outputs)
        form = context.definition_json.get("form", {})
        self._field_validator.validate_form(
            self._form_fields(context),
            clean_outputs,
            cross_field_constraints=form.get("crossFieldConstraints"),
        )
        self._validate_declared_output(context, clean_outputs)

    def _validate_declared_output(
        self, context: ExecutionContext, outputs: dict[str, Any]
    ) -> None:
        output_decl = declared_output(context.definition_json)
        if output_decl is None:
            return

        output_id = output_decl["id"]
        value = outputs.get(output_id)
        if value is None:
            raise FieldValidationError(
                f"Declared output '{output_id}' is required",
                field_errors=[
                    {
                        "field": output_id,
                        "rule": "required",
                        "message": f"Declared output '{output_id}' is required",
                    }
                ],
            )
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise FieldValidationError(
                f"Declared output '{output_id}' must be a number",
                field_errors=[
                    {
                        "field": output_id,
                        "rule": "number",
                        "message": f"Declared output '{output_id}' must be a number",
                    }
                ],
            )

    def complete(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]:
        return self._strip_internal_keys(outputs)

    def _validate_locked_inputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
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

    @staticmethod
    def _strip_internal_keys(outputs: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in outputs.items() if not str(key).startswith("__")}
