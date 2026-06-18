from __future__ import annotations

from typing import Any

from app.domain.exceptions import FieldValidationError
from app.domain.ports.executors import ExecutionContext


class BaseNodeExecutor:
    """Template Method skeleton shared by all node executors."""

    @property
    def base_kind(self) -> str:
        raise NotImplementedError

    def prepare(self, context: ExecutionContext) -> dict[str, Any]:
        fields = self._form_fields(context)
        if not fields:
            return dict(context.resolved_inputs)

        defaults: dict[str, Any] = {}
        for field in fields:
            field_id = str(field["id"])
            if field_id in context.resolved_inputs:
                defaults[field_id] = context.resolved_inputs[field_id]
        return defaults

    def prepare_form_fields(self, context: ExecutionContext) -> list[dict[str, Any]]:
        fields: list[dict[str, Any]] = []
        for field in self._form_fields(context):
            enriched = dict(field)
            field_id = str(field["id"])
            if field_id in context.resolved_inputs:
                enriched["defaultValue"] = context.resolved_inputs[field_id]
            fields.append(enriched)
        return fields

    @staticmethod
    def _form_fields(context: ExecutionContext) -> list[dict[str, Any]]:
        return context.definition_json.get("form", {}).get("fields", [])

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
