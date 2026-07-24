"""Port: workflow / node projection persistence."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ProjectionRepositoryPort(Protocol):
    def get_workflow_state(self, workflow_instance_id: str) -> dict[str, Any] | None: ...

    def get_workflow_states_for_instances(
        self, workflow_instance_ids: list[str]
    ) -> dict[str, dict[str, Any] | None]: ...

    def upsert_workflow_projection(
        self, *, workflow_instance_id: str, current_state_json: dict[str, Any]
    ) -> Any: ...

    def delete_projections_for_instance(self, workflow_instance_id: str) -> None: ...

    def get_node_values_map_for_instance(
        self, workflow_instance_id: str
    ) -> dict[str, dict[str, Any]]: ...

    def get_node_values_by_graph_id(
        self, *, workflow_instance_id: str, workflow_node_id: str
    ) -> dict[str, Any] | None: ...

    def clear_node_projection(self, workflow_node_instance_id: str) -> None: ...

    def upsert_node_projection(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_instance_id: str,
        current_values_json: dict[str, Any],
    ) -> Any: ...
