from uuid import uuid4

from sqlalchemy import select

from app.domain.exceptions import NotFoundError, VersionConflictError
from app.infrastructure.db.models import (
    NodeStatus,
    WorkflowInstance,
    WorkflowNodeInstance,
    WorkflowSnapshot,
    WorkflowStatus,
)
from app.infrastructure.db.repositories.base import BaseRepository


class InstanceRepository(BaseRepository):
    def create_workflow_instance(
        self,
        *,
        name: str,
        workflow_definition_id: str,
        workflow_definition_version_id: str,
        status: WorkflowStatus = WorkflowStatus.PENDING,
        created_by: str | None = None,
        instance_id: str | None = None,
    ) -> WorkflowInstance:
        instance = WorkflowInstance(
            id=instance_id or str(uuid4()),
            name=name,
            workflow_definition_id=workflow_definition_id,
            workflow_definition_version_id=workflow_definition_version_id,
            status=status,
            created_by=created_by,
        )
        self.session.add(instance)
        self.session.flush()
        return instance

    def create_snapshot(
        self, *, workflow_instance_id: str, snapshot_json: dict
    ) -> WorkflowSnapshot:
        snapshot = WorkflowSnapshot(
            workflow_instance_id=workflow_instance_id,
            snapshot_json=snapshot_json,
        )
        self.session.add(snapshot)
        self.session.flush()
        return snapshot

    def create_node_instance(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        node_definition_version_id: str,
        status: NodeStatus = NodeStatus.WAITING,
        node_instance_id: str | None = None,
    ) -> WorkflowNodeInstance:
        node_instance = WorkflowNodeInstance(
            id=node_instance_id or str(uuid4()),
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=workflow_node_id,
            node_definition_version_id=node_definition_version_id,
            status=status,
        )
        self.session.add(node_instance)
        self.session.flush()
        return node_instance

    def get_workflow_instance(self, instance_id: str) -> WorkflowInstance | None:
        return self.session.get(WorkflowInstance, instance_id)

    def list_node_instances(self, workflow_instance_id: str) -> list[WorkflowNodeInstance]:
        return list(
            self.session.scalars(
                select(WorkflowNodeInstance).where(
                    WorkflowNodeInstance.workflow_instance_id == workflow_instance_id
                )
            )
        )

    def get_node_instance(self, node_instance_id: str) -> WorkflowNodeInstance | None:
        return self.session.get(WorkflowNodeInstance, node_instance_id)

    def update_workflow_status(
        self,
        instance: WorkflowInstance,
        status: WorkflowStatus,
        *,
        expected_revision: int | None = None,
    ) -> WorkflowInstance:
        if expected_revision is not None and instance.current_revision != expected_revision:
            raise VersionConflictError(
                f"Workflow instance revision conflict: expected {expected_revision}, "
                f"got {instance.current_revision}"
            )
        instance.status = status
        instance.current_revision += 1
        self.session.flush()
        return instance

    def require_workflow_instance(self, instance_id: str) -> WorkflowInstance:
        instance = self.get_workflow_instance(instance_id)
        if instance is None:
            raise NotFoundError(f"Workflow instance not found: {instance_id}")
        return instance
