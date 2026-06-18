from __future__ import annotations

from typing import Any


class InMemoryNodeProjectionReader:
    """In-memory projection store for unit tests."""

    def __init__(self) -> None:
        self._values: dict[tuple[str, str], dict[str, Any]] = {}

    def set_values(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        values: dict[str, Any],
    ) -> None:
        self._values[(workflow_instance_id, workflow_node_id)] = dict(values)

    def get_node_values(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
    ) -> dict[str, Any] | None:
        stored = self._values.get((workflow_instance_id, workflow_node_id))
        return dict(stored) if stored is not None else None
