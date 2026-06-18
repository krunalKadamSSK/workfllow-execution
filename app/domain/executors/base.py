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
        return dict(context.resolved_inputs)

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
