"""Port: reads materialized node output values for upstream input resolution."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class NodeProjectionReader(Protocol):
    def get_node_values(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
    ) -> dict[str, Any] | None: ...
