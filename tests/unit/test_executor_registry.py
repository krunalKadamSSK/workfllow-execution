import pytest

from app.domain.exceptions import NodeExecutionError
from app.domain.executors.registry import NodeExecutorRegistry, create_default_registry
from app.domain.executors.user_input import UserInputExecutor


def test_default_registry_registers_user_input():
    registry = create_default_registry()
    assert registry.registered_kinds() == frozenset({"userInput"})


def test_registry_get_executor():
    registry = create_default_registry()
    executor = registry.get("userInput")
    assert isinstance(executor, UserInputExecutor)


def test_registry_unknown_kind_raises():
    registry = NodeExecutorRegistry()
    registry.register(UserInputExecutor())
    with pytest.raises(NodeExecutionError):
        registry.get("unknown")
