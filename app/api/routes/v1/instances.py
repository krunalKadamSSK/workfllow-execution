"""Instance routes — validation, auth hooks, and DI only."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from app.api.controllers.interfaces import InstanceCommandController, InstanceQueryController
from app.api.deps import (
    get_instance_command_controller,
    get_instance_query_controller,
    get_pagination_params,
)
from app.api.schemas.common.pagination import PageResult, PaginationParams
from app.api.schemas.v1.instances import (
    InvalidateDownstreamRequest,
    RfqIncompleteCheckResponse,
    StartWorkflowRequest,
    SubmitNodeOutputsRequest,
    WorkflowEventResponse,
    WorkflowInstanceResponse,
    WorkflowInstanceSummaryResponse,
    WorkflowNodeExecutionResponse,
    WorkflowRevisionRequest,
)
from app.domain.enums import ExecutionStatus, WorkflowStatus

router = APIRouter(prefix="/instances", tags=["instances"])


@router.post("", response_model=WorkflowInstanceResponse, status_code=201)
def start_workflow(
    payload: StartWorkflowRequest,
    controller: InstanceCommandController = Depends(get_instance_command_controller),
) -> WorkflowInstanceResponse:
    return controller.start_workflow(payload)


@router.get("", response_model=PageResult[WorkflowInstanceSummaryResponse])
def list_instances(
    rfqId: str = Query(..., min_length=1, description="RFQ id to list workflow revisions for"),
    incompleteOnly: bool = Query(
        False,
        description="When true, only PENDING/RUNNING/PAUSED instances are returned",
    ),
    status: WorkflowStatus | None = Query(None),
    createdFrom: datetime | None = Query(None),
    createdTo: datetime | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination_params),
    controller: InstanceQueryController = Depends(get_instance_query_controller),
) -> PageResult[WorkflowInstanceSummaryResponse]:
    return controller.list_instances(
        rfq_id=rfqId,
        incomplete_only=incompleteOnly,
        pagination=pagination,
        status=status,
        created_from=createdFrom,
        created_to=createdTo,
    )


@router.get("/rfq/{rfq_id}/incomplete", response_model=RfqIncompleteCheckResponse)
def check_incomplete_revision(
    rfq_id: str,
    controller: InstanceQueryController = Depends(get_instance_query_controller),
) -> RfqIncompleteCheckResponse:
    return controller.check_incomplete_revision(rfq_id=rfq_id)


@router.get("/export")
def export_all_instances(
    controller: InstanceQueryController = Depends(get_instance_query_controller),
) -> Response:
    return controller.export_all_instances()


@router.get("/{instance_id}/export")
def export_instance(
    instance_id: str,
    controller: InstanceQueryController = Depends(get_instance_query_controller),
) -> Response:
    return controller.export_instance(instance_id=instance_id)


@router.get("/{instance_id}", response_model=WorkflowInstanceResponse)
def get_instance(
    instance_id: str,
    controller: InstanceQueryController = Depends(get_instance_query_controller),
) -> WorkflowInstanceResponse:
    return controller.get_instance(instance_id=instance_id)


@router.post(
    "/{instance_id}/nodes/{workflow_node_id}/submit",
    response_model=WorkflowInstanceResponse,
)
def submit_node_outputs(
    instance_id: str,
    workflow_node_id: str,
    payload: SubmitNodeOutputsRequest,
    controller: InstanceCommandController = Depends(get_instance_command_controller),
) -> WorkflowInstanceResponse:
    return controller.submit_node_outputs(
        instance_id=instance_id,
        workflow_node_id=workflow_node_id,
        payload=payload,
    )


@router.post(
    "/{instance_id}/nodes/{workflow_node_id}/invalidate",
    response_model=WorkflowInstanceResponse,
)
def reopen_from_task(
    instance_id: str,
    workflow_node_id: str,
    payload: InvalidateDownstreamRequest,
    controller: InstanceCommandController = Depends(get_instance_command_controller),
) -> WorkflowInstanceResponse:
    return controller.reopen_from_task(
        instance_id=instance_id,
        workflow_node_id=workflow_node_id,
        payload=payload,
    )


@router.post("/{instance_id}/pause", response_model=WorkflowInstanceResponse)
def pause_workflow(
    instance_id: str,
    payload: WorkflowRevisionRequest | None = None,
    controller: InstanceCommandController = Depends(get_instance_command_controller),
) -> WorkflowInstanceResponse:
    return controller.pause_workflow(instance_id=instance_id, payload=payload)


@router.post("/{instance_id}/resume", response_model=WorkflowInstanceResponse)
def resume_workflow(
    instance_id: str,
    payload: WorkflowRevisionRequest | None = None,
    controller: InstanceCommandController = Depends(get_instance_command_controller),
) -> WorkflowInstanceResponse:
    return controller.resume_workflow(instance_id=instance_id, payload=payload)


@router.post("/{instance_id}/cancel", response_model=WorkflowInstanceResponse)
def cancel_workflow(
    instance_id: str,
    payload: WorkflowRevisionRequest | None = None,
    controller: InstanceCommandController = Depends(get_instance_command_controller),
) -> WorkflowInstanceResponse:
    return controller.cancel_workflow(instance_id=instance_id, payload=payload)


@router.get("/{instance_id}/events", response_model=PageResult[WorkflowEventResponse])
def list_events(
    instance_id: str,
    afterSequence: int | None = Query(None, ge=0),
    eventType: str | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination_params),
    controller: InstanceQueryController = Depends(get_instance_query_controller),
) -> PageResult[WorkflowEventResponse]:
    return controller.list_events(
        instance_id=instance_id,
        pagination=pagination,
        after_sequence=afterSequence,
        event_type=eventType,
    )


@router.get(
    "/{instance_id}/node-executions",
    response_model=PageResult[WorkflowNodeExecutionResponse],
)
def list_node_executions(
    instance_id: str,
    workflowNodeId: str | None = Query(None),
    status: ExecutionStatus | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination_params),
    controller: InstanceQueryController = Depends(get_instance_query_controller),
) -> PageResult[WorkflowNodeExecutionResponse]:
    return controller.list_node_executions(
        instance_id=instance_id,
        pagination=pagination,
        workflow_node_id=workflowNodeId,
        status=status,
    )
