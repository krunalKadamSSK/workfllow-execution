from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.api.schemas.v1.instances import (
    WorkflowInstanceResponse,
    WorkflowInstanceSummaryResponse,
)


@runtime_checkable
class InstanceResponseMapper(Protocol):
    def map_instance_response(self, state: dict) -> WorkflowInstanceResponse: ...

    def map_instance_summary(self, instance: object) -> WorkflowInstanceSummaryResponse: ...
