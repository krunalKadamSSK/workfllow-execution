from __future__ import annotations

from typing import Any

from app.domain.enums import NodeStatus


class DbNodeProjectionReader:
    """Adapter: SQLAlchemy projection repository -> NodeProjectionReader port."""

    def __init__(self, projection_repository, instance_repository=None) -> None:
        self._repository = projection_repository
        self._instances = instance_repository

    def get_node_values(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
    ) -> dict[str, Any] | None:
        if self._instances is not None:
            node_instance = self._instances.get_node_instance_by_graph_id(
                workflow_instance_id,
                workflow_node_id,
            )
            if node_instance is None or node_instance.status != NodeStatus.COMPLETED:
                return None

        values = self._repository.get_node_values_by_graph_id(
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=workflow_node_id,
        )
        if values is None or len(values) == 0:
            return None
        return values


class PrefetchedNodeProjectionReader:
    """In-memory NodeProjectionReader backed by batch-loaded maps."""

    def __init__(
        self,
        *,
        values_by_graph_id: dict[str, dict[str, Any]],
        statuses_by_graph_id: dict[str, NodeStatus],
    ) -> None:
        self._values_by_graph_id = values_by_graph_id
        self._statuses_by_graph_id = statuses_by_graph_id

    def get_node_values(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
    ) -> dict[str, Any] | None:
        _ = workflow_instance_id
        if self._statuses_by_graph_id.get(workflow_node_id) != NodeStatus.COMPLETED:
            return None
        values = self._values_by_graph_id.get(workflow_node_id)
        if values is None or len(values) == 0:
            return None
        return values
