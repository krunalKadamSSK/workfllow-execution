"""Node execution list/query actions (JOIN batch reads)."""

from sqlalchemy import select

from app.application.common.dto.pagination import Page, PageRequest
from app.domain.enums import ExecutionStatus
from app.infrastructure.persistence.models import WorkflowNodeExecution, WorkflowNodeInstance
from app.infrastructure.persistence.paginator import SqlAlchemyQueryPaginator
from app.infrastructure.persistence.repositories.base import BaseRepository


class NodeExecutionQueryMixin(BaseRepository):
    """Mixin providing batched execution log queries."""

    def list_node_executions(self, workflow_instance_id: str) -> list[WorkflowNodeExecution]:
        return list(
            self.session.scalars(self._build_node_executions_statement(workflow_instance_id))
        )

    def list_node_execution_rows(
        self,
        workflow_instance_id: str,
        *,
        workflow_node_id: str | None = None,
        status: ExecutionStatus | None = None,
    ) -> list:
        statement = self._build_node_execution_join_statement(
            workflow_instance_id,
            workflow_node_id=workflow_node_id,
            status=status,
        )
        return list(self.session.execute(statement).all())

    def list_node_executions_page(
        self,
        workflow_instance_id: str,
        page: PageRequest,
        *,
        workflow_node_id: str | None = None,
        status: ExecutionStatus | None = None,
    ) -> Page:
        statement = self._build_node_execution_join_statement(
            workflow_instance_id,
            workflow_node_id=workflow_node_id,
            status=status,
        )
        return SqlAlchemyQueryPaginator().fetch_page_rows(self.session, statement, page)

    def list_all_node_executions(self) -> list[WorkflowNodeExecution]:
        return list(
            self.session.scalars(
                select(WorkflowNodeExecution).order_by(WorkflowNodeExecution.started_at)
            )
        )

    def _build_node_execution_join_statement(
        self,
        workflow_instance_id: str,
        *,
        workflow_node_id: str | None = None,
        status: ExecutionStatus | None = None,
    ):
        statement = (
            select(WorkflowNodeExecution, WorkflowNodeInstance)
            .join(
                WorkflowNodeInstance,
                WorkflowNodeExecution.workflow_node_instance_id == WorkflowNodeInstance.id,
            )
            .where(WorkflowNodeExecution.workflow_instance_id == workflow_instance_id)
        )
        if workflow_node_id is not None:
            statement = statement.where(
                WorkflowNodeInstance.workflow_node_id == workflow_node_id
            )
        if status is not None:
            statement = statement.where(WorkflowNodeExecution.status == status)
        return statement.order_by(WorkflowNodeExecution.started_at)

    def _build_node_executions_statement(self, workflow_instance_id: str):
        return (
            select(WorkflowNodeExecution)
            .where(WorkflowNodeExecution.workflow_instance_id == workflow_instance_id)
            .order_by(WorkflowNodeExecution.started_at)
        )
