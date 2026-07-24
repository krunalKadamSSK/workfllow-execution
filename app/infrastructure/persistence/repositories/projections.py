from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.infrastructure.persistence.models.instances import WorkflowNodeInstance
from app.infrastructure.persistence.models.projections import (
    WorkflowNodeProjection,
    WorkflowProjection,
)
from app.infrastructure.persistence.repositories.base import BaseRepository


class ProjectionRepository(BaseRepository):
    def get_workflow_state(self, workflow_instance_id: str) -> dict[str, Any] | None:
        return self.session.scalar(
            select(WorkflowProjection.current_state_json).where(
                WorkflowProjection.workflow_instance_id == workflow_instance_id
            )
        )

    def get_workflow_states_for_instances(
        self, workflow_instance_ids: list[str]
    ) -> dict[str, dict[str, Any] | None]:
        unique_ids = [instance_id for instance_id in workflow_instance_ids if instance_id]
        result: dict[str, dict[str, Any] | None] = {
            instance_id: None for instance_id in unique_ids
        }
        if not unique_ids:
            return result
        rows = self.session.execute(
            select(
                WorkflowProjection.workflow_instance_id,
                WorkflowProjection.current_state_json,
            ).where(WorkflowProjection.workflow_instance_id.in_(unique_ids))
        )
        for instance_id, state_json in rows:
            result[instance_id] = state_json if isinstance(state_json, dict) else None
        return result

    def upsert_workflow_projection(
        self,
        *,
        workflow_instance_id: str,
        current_state_json: dict[str, Any],
    ) -> WorkflowProjection:
        existing = self.session.scalar(
            select(WorkflowProjection).where(
                WorkflowProjection.workflow_instance_id == workflow_instance_id
            )
        )
        if existing is not None:
            existing.current_state_json = current_state_json
            self.session.flush()
            return existing

        projection = WorkflowProjection(
            workflow_instance_id=workflow_instance_id,
            current_state_json=current_state_json,
        )
        self.session.add(projection)
        self.session.flush()
        return projection

    def delete_projections_for_instance(self, workflow_instance_id: str) -> None:
        workflow_projection = self.session.scalar(
            select(WorkflowProjection).where(
                WorkflowProjection.workflow_instance_id == workflow_instance_id
            )
        )
        if workflow_projection is not None:
            self.session.delete(workflow_projection)

        node_projections = self.session.scalars(
            select(WorkflowNodeProjection).where(
                WorkflowNodeProjection.workflow_instance_id == workflow_instance_id
            )
        )
        for projection in node_projections:
            self.session.delete(projection)
        self.session.flush()

    def get_node_values_by_graph_id(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
    ) -> dict[str, Any] | None:
        return self.session.scalar(
            select(WorkflowNodeProjection.current_values_json)
            .join(
                WorkflowNodeInstance,
                WorkflowNodeProjection.workflow_node_instance_id == WorkflowNodeInstance.id,
            )
            .where(
                WorkflowNodeInstance.workflow_instance_id == workflow_instance_id,
                WorkflowNodeInstance.workflow_node_id == workflow_node_id,
            )
        )

    def get_node_values_map_for_instance(
        self, workflow_instance_id: str
    ) -> dict[str, dict[str, Any]]:
        """Return node projection values keyed by workflow graph node id."""
        rows = self.session.execute(
            select(
                WorkflowNodeInstance.workflow_node_id,
                WorkflowNodeProjection.current_values_json,
            )
            .join(
                WorkflowNodeProjection,
                WorkflowNodeProjection.workflow_node_instance_id == WorkflowNodeInstance.id,
            )
            .where(WorkflowNodeInstance.workflow_instance_id == workflow_instance_id)
        )
        return {
            workflow_node_id: dict(values_json)
            for workflow_node_id, values_json in rows
            if isinstance(values_json, dict)
        }

    def clear_node_projection(self, workflow_node_instance_id: str) -> None:
        existing = self.session.scalar(
            select(WorkflowNodeProjection).where(
                WorkflowNodeProjection.workflow_node_instance_id == workflow_node_instance_id
            )
        )
        if existing is not None:
            existing.current_values_json = {}
            self.session.flush()

    def upsert_node_projection(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_instance_id: str,
        current_values_json: dict[str, Any],
    ) -> WorkflowNodeProjection:
        existing = self.session.scalar(
            select(WorkflowNodeProjection).where(
                WorkflowNodeProjection.workflow_node_instance_id == workflow_node_instance_id
            )
        )
        if existing is not None:
            existing.current_values_json = current_values_json
            self.session.flush()
            return existing

        projection = WorkflowNodeProjection(
            workflow_instance_id=workflow_instance_id,
            workflow_node_instance_id=workflow_node_instance_id,
            current_values_json=current_values_json,
        )
        self.session.add(projection)
        self.session.flush()
        return projection
