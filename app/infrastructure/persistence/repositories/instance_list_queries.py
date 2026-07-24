"""Workflow instance list/query actions (RFQ filters + pagination)."""

from sqlalchemy import select

from app.application.common.dto.pagination import Page, PageRequest
from app.domain.enums import WorkflowStatus
from app.infrastructure.persistence.models import WorkflowInstance
from app.infrastructure.persistence.paginator import SqlAlchemyQueryPaginator
from app.infrastructure.persistence.repositories.base import BaseRepository

INCOMPLETE_WORKFLOW_STATUSES: frozenset[WorkflowStatus] = frozenset(
    {
        WorkflowStatus.PENDING,
        WorkflowStatus.RUNNING,
        WorkflowStatus.PAUSED,
    }
)


class InstanceListQueryMixin(BaseRepository):
    """Mixin providing RFQ-scoped instance list queries."""

    def list_workflow_instances(self) -> list[WorkflowInstance]:
        return list(
            self.session.scalars(
                select(WorkflowInstance).order_by(WorkflowInstance.created_at.desc())
            )
        )

    def list_by_rfq_id(
        self,
        rfq_id: str,
        *,
        incomplete_only: bool = False,
    ) -> list[WorkflowInstance]:
        statement = self._build_rfq_list_statement(rfq_id, incomplete_only=incomplete_only)
        return list(self.session.scalars(statement))

    def list_by_rfq_id_page(
        self,
        rfq_id: str,
        page: PageRequest,
        *,
        incomplete_only: bool = False,
        status: WorkflowStatus | None = None,
        created_from=None,
        created_to=None,
    ) -> Page[WorkflowInstance]:
        statement = self._build_rfq_list_statement(
            rfq_id,
            incomplete_only=incomplete_only,
            status=status,
            created_from=created_from,
            created_to=created_to,
        )
        return SqlAlchemyQueryPaginator().fetch_page(self.session, statement, page)

    def _build_rfq_list_statement(
        self,
        rfq_id: str,
        *,
        incomplete_only: bool,
        status: WorkflowStatus | None = None,
        created_from=None,
        created_to=None,
    ):
        statement = select(WorkflowInstance).where(WorkflowInstance.rfq_id == rfq_id.strip())
        if incomplete_only:
            statement = statement.where(
                WorkflowInstance.status.in_(tuple(INCOMPLETE_WORKFLOW_STATUSES))
            )
        if status is not None:
            statement = statement.where(WorkflowInstance.status == status)
        if created_from is not None:
            statement = statement.where(WorkflowInstance.created_at >= created_from)
        if created_to is not None:
            statement = statement.where(WorkflowInstance.created_at <= created_to)
        return statement.order_by(WorkflowInstance.created_at.desc())

    def has_incomplete_for_rfq(self, rfq_id: str) -> bool:
        statement = (
            select(WorkflowInstance.id)
            .where(
                WorkflowInstance.rfq_id == rfq_id.strip(),
                WorkflowInstance.status.in_(tuple(INCOMPLETE_WORKFLOW_STATUSES)),
            )
            .limit(1)
        )
        return self.session.scalar(statement) is not None
