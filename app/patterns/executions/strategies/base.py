"""Template Method ABC for task-type strategies (runtime polymorphism)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.domain.exceptions import FieldValidationError
from app.domain.ports.execution_context import ExecutionContext
from app.domain.seed.field_classifier import FieldSeedClassifier, filter_static_outputs
from app.domain.validation.issues import ValidationIssue


class BaseNodeExecutor(ABC):
    """Strategy + Template Method for one ``baseKind``.

    Subclasses own validate/create/execute behavior. The registry is the only
    place that maps the ``baseKind`` string to a concrete strategy.
    """

    @property
    @abstractmethod
    def base_kind(self) -> str:
        raise NotImplementedError

    def runs_automatically(self) -> bool:
        """When True, ``GraphRuntime.advance`` executes the node without UI submit."""
        return False

    def normalize_definition_json(self, definition_json: dict[str, Any]) -> dict[str, Any]:
        """Fill kind-specific defaults when persisting a node definition."""
        return definition_json

    def validate_definition(self, definition_json: dict[str, Any]) -> list[ValidationIssue]:
        """Publish-time validation for this task type."""
        return []

    def extract_seed_defaults(
        self,
        definition_json: dict[str, Any],
        outputs: dict[str, Any],
        *,
        classifier: FieldSeedClassifier,
    ) -> dict[str, Any]:
        """Static defaults captured from a prior revision for this task type."""
        fields = definition_json.get("form", {}).get("fields", [])
        if not isinstance(fields, list):
            return {}
        return filter_static_outputs(
            outputs=outputs,
            fields=fields,
            classifier=classifier,
        )

    def declared_output(self, definition_json: dict[str, Any]) -> dict[str, str] | None:
        output = definition_json.get("output")
        if not isinstance(output, dict):
            return None
        output_id = output.get("id")
        if not isinstance(output_id, str) or not output_id:
            return None
        label = output.get("label")
        return {
            "id": output_id,
            "label": label if isinstance(label, str) and label else output_id,
        }

    def collect_input_field_ids(self, definition_json: dict[str, Any]) -> set[str]:
        field_ids: set[str] = set()
        form = definition_json.get("form") or {}
        for field in form.get("fields") or []:
            if isinstance(field, dict) and "id" in field:
                field_ids.add(str(field["id"]))
        return field_ids

    def collect_output_field_ids(self, definition_json: dict[str, Any]) -> set[str]:
        field_ids = self.collect_input_field_ids(definition_json)
        output_decl = self.declared_output(definition_json)
        if output_decl is not None:
            field_ids.add(output_decl["id"])
        return field_ids

    def cost_contribution(
        self, definition_json: dict[str, Any], outputs: dict[str, Any]
    ) -> float | None:
        output_decl = self.declared_output(definition_json)
        if output_decl is None:
            return None
        value = outputs.get(output_decl["id"])
        if isinstance(value, bool) or not isinstance(value, int | float):
            return None
        return float(value)

    def prepare(self, context: ExecutionContext) -> dict[str, Any]:
        fields = self._form_fields(context)
        if not fields:
            return {**dict(context.seed_defaults), **dict(context.resolved_inputs)}

        defaults: dict[str, Any] = {}
        for field in fields:
            field_id = str(field["id"])
            if field_id in context.resolved_inputs:
                defaults[field_id] = context.resolved_inputs[field_id]
            elif field_id in context.seed_defaults:
                defaults[field_id] = context.seed_defaults[field_id]
        return defaults

    def prepare_form_fields(self, context: ExecutionContext) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for field in self._form_fields(context):
            enriched = dict(field)
            field_id = str(field["id"])
            if field_id in context.resolved_inputs:
                enriched["defaultValue"] = context.resolved_inputs[field_id]
            elif field_id in context.seed_defaults:
                enriched["defaultValue"] = context.seed_defaults[field_id]
            fields.append(enriched)
        return fields

    def prepare_pending_node_form(self, context: ExecutionContext) -> dict[str, Any]:
        return {
            "formKind": "synapse",
            "fields": self.prepare_form_fields(context),
        }

    @staticmethod
    def _form_fields(context: ExecutionContext) -> list[dict[str, Any]]:
        return context.definition_json.get("form", {}).get("fields", [])

    @staticmethod
    def _strip_internal_keys(outputs: dict[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in outputs.items() if not str(key).startswith("__")}

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

    def validate_outputs(self, context: ExecutionContext, outputs: dict[str, Any]) -> None:
        return None

    def complete(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]:
        return outputs

    def run(self, context: ExecutionContext, outputs: dict[str, Any]) -> dict[str, Any]:
        merged = {**self.prepare(context), **outputs}
        try:
            self.validate_outputs(context, merged)
        except FieldValidationError:
            raise
        except Exception as exc:
            raise FieldValidationError(str(exc)) from exc
        return self.complete(context, merged)

    def on_ready(self, context: ExecutionContext) -> dict[str, Any]:
        """Outputs used when ``runs_automatically()`` is True (default empty)."""
        return {}
