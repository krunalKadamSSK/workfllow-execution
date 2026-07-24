from __future__ import annotations

from app.domain.exceptions import NodeExecutionError
from app.patterns.executions.strategies.base import BaseNodeExecutor
from app.patterns.executions.strategies.table_input import TableExecutor
from app.patterns.executions.strategies.user_input import UserInputExecutor


class NodeExecutorRegistry:
    """Factory Method registry: ``baseKind`` → task-type strategy."""

    def __init__(self) -> None:
        self._executors: dict[str, BaseNodeExecutor] = {}

    def register(self, executor: BaseNodeExecutor) -> None:
        self._executors[executor.base_kind] = executor

    def get(self, base_kind: str) -> BaseNodeExecutor:
        executor = self._executors.get(base_kind)
        if executor is None:
            raise NodeExecutionError(f"No executor registered for baseKind '{base_kind}'")
        return executor

    def for_definition(self, definition_json: dict) -> BaseNodeExecutor:
        kind = str(definition_json.get("baseKind") or "userInput")
        return self.get(kind)

    def normalize_definition(self, definition_json: dict) -> dict:
        kind = str(definition_json.get("baseKind") or "")
        executor = self._executors.get(kind)
        if executor is None:
            return definition_json
        return executor.normalize_definition_json(definition_json)

    def registered_kinds(self) -> frozenset[str]:
        return frozenset(self._executors)


_DEFAULT_REGISTRY: NodeExecutorRegistry | None = None


def create_default_registry() -> NodeExecutorRegistry:
    registry = NodeExecutorRegistry()
    registry.register(UserInputExecutor())
    registry.register(TableExecutor())
    return registry


def get_default_registry() -> NodeExecutorRegistry:
    """Process-wide default registry for helpers that cannot take DI."""
    global _DEFAULT_REGISTRY
    if _DEFAULT_REGISTRY is None:
        _DEFAULT_REGISTRY = create_default_registry()
    return _DEFAULT_REGISTRY
