from __future__ import annotations

from datetime import datetime
from typing import Protocol, runtime_checkable

from fastapi.responses import Response

from app.api.schemas.common.pagination import PageResult, PaginationParams
from app.api.schemas.v1.instances import (
    RfqIncompleteCheckResponse,
    WorkflowEventResponse,
    WorkflowInstanceResponse,
    WorkflowInstanceSummaryResponse,
    WorkflowNodeExecutionResponse,
)
from app.domain.enums import ExecutionStatus, WorkflowStatus


@runtime_checkable
class InstanceQueryController(Protocol):
    def get_instance(self, *, instance_id: str) -> WorkflowInstanceResponse: ...

    def list_instances(
        self,
        *,
        rfq_id: str,
        incomplete_only: bool,
        pagination: PaginationParams,
        status: WorkflowStatus | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> PageResult[WorkflowInstanceSummaryResponse]: ...

    def check_incomplete_revision(self, *, rfq_id: str) -> RfqIncompleteCheckResponse: ...

    def export_all_instances(self) -> Response: ...

    def export_instance(self, *, instance_id: str) -> Response: ...

    def list_events(
        self,
        *,
        instance_id: str,
        pagination: PaginationParams,
        after_sequence: int | None = None,
        event_type: str | None = None,
    ) -> PageResult[WorkflowEventResponse]: ...

    def list_node_executions(
        self,
        *,
        instance_id: str,
        pagination: PaginationParams,
        workflow_node_id: str | None = None,
        status: ExecutionStatus | None = None,
    ) -> PageResult[WorkflowNodeExecutionResponse]: ...
