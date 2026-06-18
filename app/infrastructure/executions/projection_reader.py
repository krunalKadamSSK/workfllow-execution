from __future__ import annotations

from typing import Any


class DbNodeProjectionReader:
    """Adapter: SQLAlchemy projection repository -> NodeProjectionReader port."""

    def __init__(self, projection_repository) -> None:
        self._repository = projection_repository

    def get_node_values(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
    ) -> dict[str, Any] | None:
        return self._repository.get_node_values_by_graph_id(
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=workflow_node_id,
        )
