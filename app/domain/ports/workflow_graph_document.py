"""Port: duck-typed workflow definition document for domain validation."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class WorkflowGraphDocument(Protocol):
    """Minimal surface used by graph / wiring validators (no API schema import)."""

    nodes: Sequence[Any]
    edges: Sequence[Any]

    def task_nodes(self) -> Sequence[Any]: ...
