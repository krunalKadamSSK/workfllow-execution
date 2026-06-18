from __future__ import annotations

from typing import Any

from sqlalchemy import select

from app.infrastructure.db.models.instances import WorkflowNodeInstance
from app.infrastructure.db.models.projections import WorkflowNodeProjection
from app.infrastructure.db.repositories.base import BaseRepository


class ProjectionRepository(BaseRepository):
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
