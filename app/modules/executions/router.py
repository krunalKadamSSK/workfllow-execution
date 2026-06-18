from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.application.executions.service import ExecutionService
from app.domain.enums import NodeStatus
from app.modules.executions.schemas import (
    PendingNodeFormResponse,
    StartWorkflowRequest,
    SubmitNodeOutputsRequest,
    WorkflowEventResponse,
    WorkflowInstanceResponse,
    WorkflowNodeInstanceResponse,
)

router = APIRouter(prefix="/instances", tags=["instances"])


def get_execution_service(session: Session = Depends(get_session)) -> ExecutionService:
    return ExecutionService.from_session(session)


def _instance_response(state: dict) -> WorkflowInstanceResponse:
    instance = state["instance"]
    return WorkflowInstanceResponse(
        id=instance.id,
        name=instance.name,
        workflow_definition_id=instance.workflow_definition_id,
        workflow_definition_version_id=instance.workflow_definition_version_id,
        status=instance.status.value,
        current_revision=instance.current_revision,
        created_at=instance.created_at,
        completed_at=instance.completed_at,
        node_instances=[
            WorkflowNodeInstanceResponse(
                id=node.id,
                workflow_node_id=node.workflow_node_id,
                node_definition_version_id=node.node_definition_version_id,
                status=node.status.value,
                current_execution=node.current_execution,
            )
            for node in state["node_instances"]
        ],
        pending_node_ids=[
            node.workflow_node_id
            for node in state["node_instances"]
            if node.status == NodeStatus.PENDING
        ],
        pending_node_forms={
            workflow_node_id: PendingNodeFormResponse(**form)
            for workflow_node_id, form in state.get("pending_node_forms", {}).items()
        },
        workflow_projection=state.get("workflow_projection"),
    )


@router.post("", response_model=WorkflowInstanceResponse, status_code=201)
def start_workflow(
    payload: StartWorkflowRequest,
    service: ExecutionService = Depends(get_execution_service),
    session: Session = Depends(get_session),
) -> WorkflowInstanceResponse:
    instance = service.start_workflow(
        name=payload.name,
        workflow_definition_id=payload.workflow_definition_id,
        version=payload.version,
        created_by=payload.created_by,
    )
    session.commit()
    state = service.get_instance_state(instance.id)
    return _instance_response(state)


@router.get("/{instance_id}", response_model=WorkflowInstanceResponse)
def get_instance(
    instance_id: str,
    service: ExecutionService = Depends(get_execution_service),
) -> WorkflowInstanceResponse:
    state = service.get_instance_state(instance_id)
    return _instance_response(state)


@router.post(
    "/{instance_id}/nodes/{workflow_node_id}/submit",
    response_model=WorkflowInstanceResponse,
)
def submit_node_outputs(
    instance_id: str,
    workflow_node_id: str,
    payload: SubmitNodeOutputsRequest,
    service: ExecutionService = Depends(get_execution_service),
    session: Session = Depends(get_session),
) -> WorkflowInstanceResponse:
    service.submit_node_outputs(
        workflow_instance_id=instance_id,
        workflow_node_id=workflow_node_id,
        outputs=payload.outputs,
        executed_by=payload.executed_by,
        expected_revision=payload.expected_revision,
    )
    session.commit()
    state = service.get_instance_state(instance_id)
    return _instance_response(state)


@router.post("/{instance_id}/pause", response_model=WorkflowInstanceResponse)
def pause_workflow(
    instance_id: str,
    service: ExecutionService = Depends(get_execution_service),
    session: Session = Depends(get_session),
) -> WorkflowInstanceResponse:
    service.pause_workflow(instance_id)
    session.commit()
    return _instance_response(service.get_instance_state(instance_id))


@router.post("/{instance_id}/resume", response_model=WorkflowInstanceResponse)
def resume_workflow(
    instance_id: str,
    service: ExecutionService = Depends(get_execution_service),
    session: Session = Depends(get_session),
) -> WorkflowInstanceResponse:
    service.resume_workflow(instance_id)
    session.commit()
    return _instance_response(service.get_instance_state(instance_id))


@router.post("/{instance_id}/cancel", response_model=WorkflowInstanceResponse)
def cancel_workflow(
    instance_id: str,
    service: ExecutionService = Depends(get_execution_service),
    session: Session = Depends(get_session),
) -> WorkflowInstanceResponse:
    service.cancel_workflow(instance_id)
    session.commit()
    return _instance_response(service.get_instance_state(instance_id))


@router.get("/{instance_id}/events", response_model=list[WorkflowEventResponse])
def list_events(
    instance_id: str,
    service: ExecutionService = Depends(get_execution_service),
) -> list[WorkflowEventResponse]:
    events = service.list_events(instance_id)
    return [
        WorkflowEventResponse(
            id=event.id,
            sequence_number=event.sequence_number,
            event_type=event.event_type,
            payload_json=event.payload_json,
            created_at=event.created_at,
        )
        for event in events
    ]
