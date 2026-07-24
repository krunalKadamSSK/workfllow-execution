"""RFQ-scoped instance list queries."""

from __future__ import annotations

from app.application.common.dto.pagination import Page, PageRequest
from app.domain.enums import WorkflowStatus
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.infrastructure.persistence.models import WorkflowInstance


class ListInstancesQuery:
    """Lists workflow instances for an RFQ (with optional filters / paging)."""

    def __init__(self, *, instances: InstanceRepository) -> None:
        self._instances = instances

    def list_instances_for_rfq(
        self,
        rfq_id: str,
        *,
        incomplete_only: bool = False,
    ) -> list[WorkflowInstance]:
        return self._instances.list_by_rfq_id(rfq_id, incomplete_only=incomplete_only)

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
        return self._instances.list_by_rfq_id_page(
            rfq_id,
            page,
            incomplete_only=incomplete_only,
            status=status,
            created_from=created_from,
            created_to=created_to,
        )

    def has_incomplete_revision(self, rfq_id: str) -> bool:
        return self._instances.has_incomplete_for_rfq(rfq_id)
