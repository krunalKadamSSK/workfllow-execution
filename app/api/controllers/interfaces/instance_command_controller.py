from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.api.schemas.v1.instances import (
    InvalidateDownstreamRequest,
    StartWorkflowRequest,
    SubmitNodeOutputsRequest,
    WorkflowInstanceResponse,
    WorkflowRevisionRequest,
)


@runtime_checkable
class InstanceCommandController(Protocol):
    def start_workflow(self, payload: StartWorkflowRequest) -> WorkflowInstanceResponse: ...

    def submit_node_outputs(
        self,
        *,
        instance_id: str,
        workflow_node_id: str,
        payload: SubmitNodeOutputsRequest,
    ) -> WorkflowInstanceResponse: ...

    def reopen_from_task(
        self,
        *,
        instance_id: str,
        workflow_node_id: str,
        payload: InvalidateDownstreamRequest,
    ) -> WorkflowInstanceResponse: ...

    def pause_workflow(
        self,
        *,
        instance_id: str,
        payload: WorkflowRevisionRequest | None,
    ) -> WorkflowInstanceResponse: ...

    def resume_workflow(
        self,
        *,
        instance_id: str,
        payload: WorkflowRevisionRequest | None,
    ) -> WorkflowInstanceResponse: ...

    def cancel_workflow(
        self,
        *,
        instance_id: str,
        payload: WorkflowRevisionRequest | None,
    ) -> WorkflowInstanceResponse: ...
