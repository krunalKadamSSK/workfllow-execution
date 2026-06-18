from __future__ import annotations

from app.domain.exceptions import NodeExecutionError
from app.domain.executors.user_input import UserInputExecutor
from app.domain.ports.executors import NodeExecutor


class NodeExecutorRegistry:
    """Factory Method registry for node executors by baseKind."""

    def __init__(self) -> None:
        self._executors: dict[str, NodeExecutor] = {}

    def register(self, executor: NodeExecutor) -> None:
        self._executors[executor.base_kind] = executor

    def get(self, base_kind: str) -> NodeExecutor:
        executor = self._executors.get(base_kind)
        if executor is None:
            raise NodeExecutionError(f"No executor registered for baseKind '{base_kind}'")
        return executor

    def registered_kinds(self) -> frozenset[str]:
        return frozenset(self._executors)


def create_default_registry() -> NodeExecutorRegistry:
    registry = NodeExecutorRegistry()
    registry.register(UserInputExecutor())
    return registry
