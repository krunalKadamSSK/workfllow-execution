"""Instance write controller — command actions (no session.commit)."""

from __future__ import annotations

from app.api.controllers.instances.response_mapper import WorkflowInstanceResponseMapper
from app.api.controllers.interfaces import InstanceResponseMapper
from app.api.schemas.v1.instances import (
    InvalidateDownstreamRequest,
    StartWorkflowRequest,
    SubmitNodeOutputsRequest,
    WorkflowInstanceResponse,
    WorkflowRevisionRequest,
)
from app.application.executions.service import ExecutionService


class WorkflowInstanceCommandController:
    """Implements ``InstanceCommandController``."""

    def __init__(
        self,
        *,
        service: ExecutionService,
        mapper: InstanceResponseMapper | None = None,
    ) -> None:
        self._service = service
        self._mapper = mapper or WorkflowInstanceResponseMapper()

    def start_workflow(self, payload: StartWorkflowRequest) -> WorkflowInstanceResponse:
        instance = self._service.start_workflow(
            name=payload.name,
            workflow_definition_id=payload.workflow_definition_id,
            version=payload.version,
            created_by=payload.created_by,
            metadata=payload.metadata,
            seed_from_instance_id=payload.seed_from_instance_id,
        )
        return self._mapper.map_instance_response(
            self._service.get_instance_state(instance.id)
        )

    def submit_node_outputs(
        self,
        *,
        instance_id: str,
        workflow_node_id: str,
        payload: SubmitNodeOutputsRequest,
    ) -> WorkflowInstanceResponse:
        self._service.submit_node_outputs(
            workflow_instance_id=instance_id,
            workflow_node_id=workflow_node_id,
            outputs=payload.outputs,
            executed_by=payload.executed_by,
            expected_revision=payload.expected_revision,
        )
        state = self._service.get_instance_state(instance_id, after_task_id=workflow_node_id)
        return self._mapper.map_instance_response(state)

    def reopen_from_task(
        self,
        *,
        instance_id: str,
        workflow_node_id: str,
        payload: InvalidateDownstreamRequest,
    ) -> WorkflowInstanceResponse:
        self._service.reopen_from_task(
            workflow_instance_id=instance_id,
            workflow_node_id=workflow_node_id,
            reason=payload.reason,
            expected_revision=payload.expected_revision,
            reopen_target=payload.reopen_target,
        )
        return self._mapper.map_instance_response(
            self._service.get_instance_state(instance_id)
        )

    def pause_workflow(
        self,
        *,
        instance_id: str,
        payload: WorkflowRevisionRequest | None,
    ) -> WorkflowInstanceResponse:
        self._service.pause_workflow(
            instance_id,
            expected_revision=payload.expected_revision if payload else None,
        )
        return self._mapper.map_instance_response(
            self._service.get_instance_state(instance_id)
        )

    def resume_workflow(
        self,
        *,
        instance_id: str,
        payload: WorkflowRevisionRequest | None,
    ) -> WorkflowInstanceResponse:
        self._service.resume_workflow(
            instance_id,
            expected_revision=payload.expected_revision if payload else None,
        )
        return self._mapper.map_instance_response(
            self._service.get_instance_state(instance_id)
        )

    def cancel_workflow(
        self,
        *,
        instance_id: str,
        payload: WorkflowRevisionRequest | None,
    ) -> WorkflowInstanceResponse:
        self._service.cancel_workflow(
            instance_id,
            expected_revision=payload.expected_revision if payload else None,
        )
        return self._mapper.map_instance_response(
            self._service.get_instance_state(instance_id)
        )
