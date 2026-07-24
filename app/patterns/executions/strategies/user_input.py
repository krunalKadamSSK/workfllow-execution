from __future__ import annotations

from typing import Any

from app.domain.exceptions import FieldValidationError
from app.domain.ports.execution_context import ExecutionContext
from app.domain.seed.field_classifier import FieldSeedClassifier, filter_static_outputs
from app.domain.validation.fields import FormFieldValidator
from app.domain.validation.form_blueprint import validate_form_blueprint
from app.domain.validation.issues import ValidationIssue
from app.patterns.executions.strategies.base import BaseNodeExecutor


class UserInputExecutor(BaseNodeExecutor):
    """Strategy for baseKind=userInput (human form tasks)."""

    def __init__(self, field_validator: FormFieldValidator | None = None) -> None:
        self._field_validator = field_validator or FormFieldValidator()

    @property
    def base_kind(self) -> str:
        return "userInput"

    def runs_automatically(self) -> bool:
        return False

    def normalize_definition_json(self, definition_json: dict[str, Any]) -> dict[str, Any]:
        payload = dict(definition_json)
        if "form" not in payload:
            payload["form"] = {"fields": [], "crossFieldConstraints": []}
        return payload

    def validate_definition(self, definition_json: dict[str, Any]) -> list[ValidationIssue]:
        form = definition_json.get("form")
        form_issues = validate_form_blueprint(form if isinstance(form, dict) else None)
        return form_issues + self._validate_declared_output_shape(definition_json)

    def extract_seed_defaults(
        self,
        definition_json: dict[str, Any],
        outputs: dict[str, Any],
        *,
        classifier: FieldSeedClassifier,
    ) -> dict[str, Any]:
        fields = definition_json.get("form", {}).get("fields", [])
        if not isinstance(fields, list):
            return {}
        return filter_static_outputs(
            outputs=outputs,
            fields=fields,
            classifier=classifier,
        )

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
        clean_outputs = self._strip_internal_keys(outputs)
        self._validate_locked_inputs(context, clean_outputs)
        form = context.definition_json.get("form", {})
        self._field_validator.validate_form(
            self._form_fields(context),
            clean_outputs,
            cross_field_constraints=form.get("crossFieldConstraints"),
        )
        self._assert_declared_output_present(context, clean_outputs)

    def _assert_declared_output_present(
        self, context: ExecutionContext, outputs: dict[str, Any]
    ) -> None:
        output_decl = self.declared_output(context.definition_json)
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
        if isinstance(value, bool) or not isinstance(value, int | float):
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

    def _validate_declared_output_shape(
        self, definition_json: dict[str, Any]
    ) -> list[ValidationIssue]:
        output = definition_json.get("output")
        if output is None:
            return []
        if not isinstance(output, dict):
            return [
                ValidationIssue(
                    code="INVALID_OUTPUT",
                    message="output must be an object",
                    field="output",
                )
            ]

        output_id = output.get("id")
        if not isinstance(output_id, str) or not output_id:
            return [
                ValidationIssue(
                    code="MISSING_OUTPUT_ID",
                    message="output.id is required",
                    field="output.id",
                )
            ]

        fields = definition_json.get("form", {}).get("fields") or []
        field_by_id: dict[str, dict[str, Any]] = {}
        for field in fields:
            if isinstance(field, dict) and field.get("id"):
                field_by_id[str(field["id"])] = field

        referenced = field_by_id.get(output_id)
        if referenced is None:
            return [
                ValidationIssue(
                    code="UNKNOWN_OUTPUT_FIELD",
                    message=f"output.id '{output_id}' does not match any form field",
                    field="output.id",
                    details={"reference": output_id},
                )
            ]

        if referenced.get("type") != "number":
            return [
                ValidationIssue(
                    code="INVALID_OUTPUT_FIELD_TYPE",
                    message="output.id must reference a number form field",
                    field="output.id",
                    details={"fieldType": referenced.get("type")},
                )
            ]

        return []
