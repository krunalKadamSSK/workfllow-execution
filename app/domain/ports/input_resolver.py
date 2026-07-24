"""Port: resolves upstream node outputs into task inputs."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class InputResolver(Protocol):
    def resolve(
        self,
        *,
        workflow_instance_id: str,
        source_node_id: str,
        output_key: str,
    ) -> Any: ...
