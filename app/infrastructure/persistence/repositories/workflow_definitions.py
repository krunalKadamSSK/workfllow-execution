"""Workflow definition persistence actions."""

from collections.abc import Iterable
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.application.common.dto.pagination import Page, PageRequest
from app.domain.exceptions import DuplicateSlugError, NotFoundError
from app.infrastructure.persistence.models import WorkflowDefinition, WorkflowDefinitionVersion
from app.infrastructure.persistence.paginator import SqlAlchemyQueryPaginator
from app.infrastructure.persistence.repositories.base import BaseRepository


class WorkflowDefinitionRepository(BaseRepository):
    def get_workflow_definitions_by_ids(
        self, definition_ids: Iterable[str]
    ) -> dict[str, WorkflowDefinition]:
        unique_ids = {definition_id for definition_id in definition_ids if definition_id}
        if not unique_ids:
            return {}
        rows = self.session.scalars(
            select(WorkflowDefinition).where(WorkflowDefinition.id.in_(unique_ids))
        )
        return {row.id: row for row in rows}

    def create_workflow_definition(
        self,
        *,
        name: str,
        slug: str,
        status: str,
        definition_json: dict,
        definition_id: str | None = None,
        created_by: str | None = None,
    ) -> tuple[WorkflowDefinition, WorkflowDefinitionVersion]:
        workflow = WorkflowDefinition(
            id=definition_id or str(uuid4()),
            name=name,
            slug=slug,
            status=status,
            latest_version=1,
        )
        version = WorkflowDefinitionVersion(
            workflow_definition_id=workflow.id,
            version=1,
            definition_json=definition_json,
            created_by=created_by,
        )
        self.session.add(workflow)
        self.session.add(version)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DuplicateSlugError(f"Workflow definition slug already exists: {slug}") from exc
        return workflow, version

    def publish_workflow_version(
        self,
        *,
        workflow_definition_id: str,
        definition_json: dict,
        created_by: str | None = None,
    ) -> WorkflowDefinitionVersion:
        workflow = self.session.get(WorkflowDefinition, workflow_definition_id)
        if workflow is None:
            raise NotFoundError(f"Workflow definition not found: {workflow_definition_id}")

        next_version = workflow.latest_version + 1
        version = WorkflowDefinitionVersion(
            workflow_definition_id=workflow.id,
            version=next_version,
            definition_json=definition_json,
            created_by=created_by,
        )
        workflow.latest_version = next_version
        self.session.add(version)
        self.session.flush()
        return version

    def get_workflow_definition_by_slug(self, slug: str) -> WorkflowDefinition | None:
        return self.session.scalar(
            select(WorkflowDefinition).where(WorkflowDefinition.slug == slug)
        )

    def get_workflow_definition(self, definition_id: str) -> WorkflowDefinition | None:
        return self.session.get(WorkflowDefinition, definition_id)

    def get_workflow_definition_version(
        self, workflow_definition_id: str, version: int
    ) -> WorkflowDefinitionVersion | None:
        return self.session.scalar(
            select(WorkflowDefinitionVersion).where(
                WorkflowDefinitionVersion.workflow_definition_id == workflow_definition_id,
                WorkflowDefinitionVersion.version == version,
            )
        )

    def get_workflow_definition_version_by_id(
        self, version_id: str
    ) -> WorkflowDefinitionVersion | None:
        return self.session.get(WorkflowDefinitionVersion, version_id)

    def list_workflow_definitions(self) -> list[WorkflowDefinition]:
        return list(
            self.session.scalars(select(WorkflowDefinition).order_by(WorkflowDefinition.name))
        )

    def list_workflow_definitions_page(
        self,
        page: PageRequest,
        *,
        status: str | None = None,
        q: str | None = None,
    ) -> Page[WorkflowDefinition]:
        statement = select(WorkflowDefinition)
        if status is not None:
            statement = statement.where(WorkflowDefinition.status == status)
        if q:
            pattern = f"%{q.strip()}%"
            statement = statement.where(
                (WorkflowDefinition.name.ilike(pattern))
                | (WorkflowDefinition.slug.ilike(pattern))
            )
        statement = statement.order_by(WorkflowDefinition.name)
        return SqlAlchemyQueryPaginator().fetch_page(self.session, statement, page)

    def list_workflow_versions_page(
        self, workflow_definition_id: str, page: PageRequest
    ) -> Page[WorkflowDefinitionVersion]:
        statement = (
            select(WorkflowDefinitionVersion)
            .where(WorkflowDefinitionVersion.workflow_definition_id == workflow_definition_id)
            .order_by(WorkflowDefinitionVersion.version.desc())
        )
        return SqlAlchemyQueryPaginator().fetch_page(self.session, statement, page)

    def pin_workflow_version(
        self, workflow_definition_id: str, version: int | None = None
    ) -> WorkflowDefinitionVersion:
        workflow = self.get_workflow_definition(workflow_definition_id)
        if workflow is None:
            raise NotFoundError(f"Workflow definition not found: {workflow_definition_id}")

        target_version = version if version is not None else workflow.latest_version
        pinned = self.get_workflow_definition_version(workflow_definition_id, target_version)
        if pinned is None:
            raise NotFoundError(
                f"Workflow definition version not found: {workflow_definition_id} v{target_version}"
            )
        return pinned
