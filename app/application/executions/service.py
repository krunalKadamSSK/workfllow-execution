"""Facade for workflow execution use-cases (commands + queries).

Write methods commit the request session (Phase 7 — controllers never commit).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.application.common.dto.pagination import Page, PageRequest
from app.application.executions.commands.control import ControlWorkflowCommand
from app.application.executions.commands.start import StartWorkflowCommand
from app.application.executions.commands.submit import SubmitNodeOutputsCommand
from app.application.executions.queries.export import ExportInstancesQuery
from app.application.executions.queries.get_instance import GetInstanceStateQuery
from app.application.executions.queries.list_instances import ListInstancesQuery
from app.application.executions.queries.node_execution_logs import NodeExecutionLogQuery
from app.domain.enums import ExecutionStatus, WorkflowStatus
from app.domain.ports.event_repository import EventRepositoryPort as EventRepository
from app.infrastructure.persistence.models import WorkflowInstance, WorkflowNodeInstance


class ExecutionService:
    """Stable application entry point for controllers."""

    def __init__(
        self,
        *,
        session: Session,
        start: StartWorkflowCommand,
        submit: SubmitNodeOutputsCommand,
        control: ControlWorkflowCommand,
        list_instances: ListInstancesQuery,
        get_instance: GetInstanceStateQuery,
        export: ExportInstancesQuery,
        node_execution_logs: NodeExecutionLogQuery,
        event_repository: EventRepository,
    ) -> None:
        self._session = session
        self._start = start
        self._submit = submit
        self._control = control
        self._list_instances = list_instances
        self._get_instance = get_instance
        self._export = export
        self._node_execution_logs = node_execution_logs
        self._event_repository = event_repository

    @classmethod
    def from_session(cls, session: Session) -> ExecutionService:
        from app.application.executions.service_factory import ExecutionServiceFactory

        return ExecutionServiceFactory.create(session)

    def _commit(self) -> None:
        self._session.commit()

    def start_workflow(
        self,
        *,
        name: str,
        workflow_definition_id: str,
        version: int | None = None,
        created_by: str | None = None,
        metadata: dict[str, Any] | None = None,
        seed_from_instance_id: str | None = None,
    ) -> WorkflowInstance:
        instance = self._start.start_workflow(
            name=name,
            workflow_definition_id=workflow_definition_id,
            version=version,
            created_by=created_by,
            metadata=metadata,
            seed_from_instance_id=seed_from_instance_id,
        )
        self._commit()
        return instance

    def list_instances_for_rfq(
        self,
        rfq_id: str,
        *,
        incomplete_only: bool = False,
    ) -> list[WorkflowInstance]:
        return self._list_instances.list_instances_for_rfq(
            rfq_id, incomplete_only=incomplete_only
        )

    def list_instances_for_rfq_page(
        self,
        rfq_id: str,
        page: PageRequest,
        *,
        incomplete_only: bool = False,
        status: WorkflowStatus | None = None,
        created_from=None,
        created_to=None,
    ) -> Page[WorkflowInstance]:
        return self._list_instances.list_instances_for_rfq_page(
            rfq_id,
            page,
            incomplete_only=incomplete_only,
            status=status,
            created_from=created_from,
            created_to=created_to,
        )

    def has_incomplete_revision(self, rfq_id: str) -> bool:
        return self._list_instances.has_incomplete_revision(rfq_id)

    def submit_node_outputs(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        outputs: dict[str, Any],
        executed_by: str | None = None,
        expected_revision: int | None = None,
    ) -> WorkflowNodeInstance:
        node = self._submit.submit_node_outputs(
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=workflow_node_id,
            outputs=outputs,
            executed_by=executed_by,
            expected_revision=expected_revision,
        )
        self._commit()
        return node

    def pause_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        instance = self._control.pause_workflow(
            workflow_instance_id, expected_revision=expected_revision
        )
        self._commit()
        return instance

    def resume_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        instance = self._control.resume_workflow(
            workflow_instance_id, expected_revision=expected_revision
        )
        self._commit()
        return instance

    def cancel_workflow(
        self, workflow_instance_id: str, *, expected_revision: int | None = None
    ) -> WorkflowInstance:
        instance = self._control.cancel_workflow(
            workflow_instance_id, expected_revision=expected_revision
        )
        self._commit()
        return instance

    def get_instance_state(
        self, workflow_instance_id: str, *, after_task_id: str | None = None
    ) -> dict[str, Any]:
        return self._get_instance.get_instance_state(
            workflow_instance_id, after_task_id=after_task_id
        )

    def list_events(self, workflow_instance_id: str):
        return self._event_repository.list_events(workflow_instance_id)

    def list_events_page(
        self,
        workflow_instance_id: str,
        page: PageRequest,
        *,
        after_sequence: int | None = None,
        event_type: str | None = None,
    ):
        return self._event_repository.list_events_page(
            workflow_instance_id,
            page,
            after_sequence=after_sequence,
            event_type=event_type,
        )

    def list_node_executions(self, workflow_instance_id: str):
        return self._node_execution_logs.list_node_executions(workflow_instance_id)

    def list_node_executions_page(
        self,
        workflow_instance_id: str,
        page: PageRequest,
        *,
        workflow_node_id: str | None = None,
        status: ExecutionStatus | None = None,
    ) -> Page[dict[str, Any]]:
        return self._node_execution_logs.list_node_executions_page(
            workflow_instance_id,
            page,
            workflow_node_id=workflow_node_id,
            status=status,
        )

    def export_instance_excel(self, workflow_instance_id: str) -> tuple[bytes, str]:
        return self._export.export_instance_excel(workflow_instance_id)

    def export_all_instances_excel(self) -> tuple[bytes, str]:
        return self._export.export_all_instances_excel()

    def invalidate_downstream(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        reason: str,
    ) -> list[WorkflowNodeInstance]:
        affected = self._control.invalidate_downstream(
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=workflow_node_id,
            reason=reason,
        )
        self._commit()
        return affected

    def reopen_from_task(
        self,
        *,
        workflow_instance_id: str,
        workflow_node_id: str,
        reason: str,
        expected_revision: int | None = None,
        reopen_target: bool = True,
    ) -> list[WorkflowNodeInstance]:
        affected = self._control.reopen_from_task(
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=workflow_node_id,
            reason=reason,
            expected_revision=expected_revision,
            reopen_target=reopen_target,
        )
        self._commit()
        return affected
