"""Instance read controller — query actions."""

from __future__ import annotations

from datetime import datetime

from fastapi.responses import Response

from app.api.controllers.instances.response_mapper import WorkflowInstanceResponseMapper
from app.api.controllers.interfaces import InstanceResponseMapper
from app.api.schemas.common.pagination import PageResult, PaginationParams
from app.api.schemas.v1.instances import (
    RfqIncompleteCheckResponse,
    WorkflowEventResponse,
    WorkflowInstanceResponse,
    WorkflowInstanceSummaryResponse,
    WorkflowNodeExecutionResponse,
)
from app.application.executions.service import ExecutionService
from app.domain.enums import ExecutionStatus, WorkflowStatus

_EXCEL_MEDIA_TYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class WorkflowInstanceQueryController:
    """Implements ``InstanceQueryController``."""

    def __init__(
        self,
        *,
        service: ExecutionService,
        mapper: InstanceResponseMapper | None = None,
    ) -> None:
        self._service = service
        self._mapper = mapper or WorkflowInstanceResponseMapper()

    def get_instance(self, *, instance_id: str) -> WorkflowInstanceResponse:
        return self._mapper.map_instance_response(
            self._service.get_instance_state(instance_id)
        )

    def list_instances(
        self,
        *,
        rfq_id: str,
        incomplete_only: bool,
        pagination: PaginationParams,
        status: WorkflowStatus | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> PageResult[WorkflowInstanceSummaryResponse]:
        page = self._service.list_instances_for_rfq_page(
            rfq_id,
            pagination.to_page_request(),
            incomplete_only=incomplete_only,
            status=status,
            created_from=created_from,
            created_to=created_to,
        )
        return PageResult[WorkflowInstanceSummaryResponse](
            items=[self._mapper.map_instance_summary(item) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    def check_incomplete_revision(self, *, rfq_id: str) -> RfqIncompleteCheckResponse:
        return RfqIncompleteCheckResponse(
            rfq_id=rfq_id,
            has_incomplete=self._service.has_incomplete_revision(rfq_id),
        )

    def export_all_instances(self) -> Response:
        content, filename = self._service.export_all_instances_excel()
        return Response(
            content=content,
            media_type=_EXCEL_MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def export_instance(self, *, instance_id: str) -> Response:
        content, filename = self._service.export_instance_excel(instance_id)
        return Response(
            content=content,
            media_type=_EXCEL_MEDIA_TYPE,
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    def list_events(
        self,
        *,
        instance_id: str,
        pagination: PaginationParams,
        after_sequence: int | None = None,
        event_type: str | None = None,
    ) -> PageResult[WorkflowEventResponse]:
        page = self._service.list_events_page(
            instance_id,
            pagination.to_page_request(),
            after_sequence=after_sequence,
            event_type=event_type,
        )
        return PageResult[WorkflowEventResponse](
            items=[
                WorkflowEventResponse(
                    id=event.id,
                    sequence_number=event.sequence_number,
                    event_type=event.event_type,
                    payload_json=event.payload_json,
                    created_at=event.created_at,
                )
                for event in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    def list_node_executions(
        self,
        *,
        instance_id: str,
        pagination: PaginationParams,
        workflow_node_id: str | None = None,
        status: ExecutionStatus | None = None,
    ) -> PageResult[WorkflowNodeExecutionResponse]:
        page = self._service.list_node_executions_page(
            instance_id,
            pagination.to_page_request(),
            workflow_node_id=workflow_node_id,
            status=status,
        )
        return PageResult[WorkflowNodeExecutionResponse](
            items=[WorkflowNodeExecutionResponse(**row) for row in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )
