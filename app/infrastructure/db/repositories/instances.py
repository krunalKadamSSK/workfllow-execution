from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from app.domain.enums import ExecutionStatus, NodeStatus, WorkflowStatus
from app.domain.exceptions import NotFoundError, VersionConflictError
from app.domain.state.node import NodeStateMachine
from app.infrastructure.db.models import (
    WorkflowInstance,
    WorkflowNodeExecution,
    WorkflowNodeInstance,
    WorkflowSnapshot,
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

    def get_node_instance_by_graph_id(
        self, workflow_instance_id: str, workflow_node_id: str
    ) -> WorkflowNodeInstance | None:
        return self.session.scalar(
            select(WorkflowNodeInstance).where(
                WorkflowNodeInstance.workflow_instance_id == workflow_instance_id,
                WorkflowNodeInstance.workflow_node_id == workflow_node_id,
            )
        )

    def require_node_instance_by_graph_id(
        self, workflow_instance_id: str, workflow_node_id: str
    ) -> WorkflowNodeInstance:
        node_instance = self.get_node_instance_by_graph_id(
            workflow_instance_id, workflow_node_id
        )
        if node_instance is None:
            raise NotFoundError(
                f"Workflow node instance not found: {workflow_node_id} "
                f"in instance {workflow_instance_id}"
            )
        return node_instance

    def update_node_status(
        self,
        node_instance: WorkflowNodeInstance,
        status: NodeStatus,
    ) -> WorkflowNodeInstance:
        NodeStateMachine().transition(node_instance.status, status)
        node_instance.status = status
        self.session.flush()
        return node_instance

    def create_node_execution(
        self,
        *,
        workflow_instance_id: str,
        node_instance: WorkflowNodeInstance,
        inputs_json: dict,
        outputs_json: dict,
        status: ExecutionStatus,
        executed_by: str | None = None,
    ) -> WorkflowNodeExecution:
        execution_number = node_instance.current_execution + 1
        node_instance.current_execution = execution_number
        execution = WorkflowNodeExecution(
            workflow_instance_id=workflow_instance_id,
            workflow_node_instance_id=node_instance.id,
            execution_number=execution_number,
            inputs_json=inputs_json,
            outputs_json=outputs_json,
            status=status,
            executed_by=executed_by,
        )
        self.session.add(execution)
        self.session.flush()
        return execution

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
        if status == WorkflowStatus.COMPLETED:
            instance.completed_at = datetime.now(timezone.utc)
        self.session.flush()
        return instance

    def get_snapshot(self, workflow_instance_id: str) -> WorkflowSnapshot | None:
        return self.session.scalar(
            select(WorkflowSnapshot).where(
                WorkflowSnapshot.workflow_instance_id == workflow_instance_id
            )
        )

    def require_workflow_instance(self, instance_id: str) -> WorkflowInstance:
        instance = self.get_workflow_instance(instance_id)
        if instance is None:
            raise NotFoundError(f"Workflow instance not found: {instance_id}")
        return instance

    def list_node_executions(self, workflow_instance_id: str) -> list[WorkflowNodeExecution]:
        return list(
            self.session.scalars(
                select(WorkflowNodeExecution)
                .where(WorkflowNodeExecution.workflow_instance_id == workflow_instance_id)
                .order_by(WorkflowNodeExecution.started_at)
            )
        )

    def list_workflow_instances(self) -> list[WorkflowInstance]:
        return list(
            self.session.scalars(
                select(WorkflowInstance).order_by(WorkflowInstance.created_at.desc())
            )
        )

    def list_all_node_instances(self) -> list[WorkflowNodeInstance]:
        return list(self.session.scalars(select(WorkflowNodeInstance)))

    def list_all_node_executions(self) -> list[WorkflowNodeExecution]:
        return list(
            self.session.scalars(
                select(WorkflowNodeExecution).order_by(WorkflowNodeExecution.started_at)
            )
        )
