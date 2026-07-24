"""Definition read controller — query actions."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.api.controllers.definitions.response_mapper import DefinitionHttpResponseMapper
from app.api.controllers.interfaces import DefinitionResponseMapper
from app.api.schemas.common.pagination import PageResult, PaginationParams
from app.api.schemas.v1.definitions.base_types import BaseTypeResponse
from app.api.schemas.v1.definitions.responses import (
    NodeDefinitionResponse,
    NodeDefinitionSummary,
    NodeDefinitionVersionSummary,
    WorkflowDefinitionResponse,
    WorkflowDefinitionSummary,
    WorkflowDefinitionVersionSummary,
)
from app.application.definitions.ingest import DefinitionIngestService


class DefinitionHttpQueryController:
    """Implements ``DefinitionQueryController`` Protocol."""

    def __init__(
        self,
        *,
        session: Session,
        mapper: DefinitionResponseMapper | None = None,
    ) -> None:
        self._session = session
        self._service = DefinitionIngestService(session)
        self._mapper = mapper or DefinitionHttpResponseMapper()

    def list_base_types(self) -> list[BaseTypeResponse]:
        return [
            BaseTypeResponse.model_validate(row) for row in self._service.list_base_types()
        ]

    def list_node_definitions(
        self,
        *,
        pagination: PaginationParams,
        status: str | None = None,
        q: str | None = None,
    ) -> PageResult[NodeDefinitionSummary]:
        page = self._service.list_nodes_page(
            pagination.to_page_request(), status=status, q=q
        )
        return PageResult[NodeDefinitionSummary](
            items=[NodeDefinitionSummary.model_validate(node) for node in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    def list_node_definition_versions(
        self, *, slug: str, pagination: PaginationParams
    ) -> PageResult[NodeDefinitionVersionSummary]:
        page = self._service.list_node_versions_page(slug, pagination.to_page_request())
        return PageResult[NodeDefinitionVersionSummary](
            items=[
                NodeDefinitionVersionSummary.model_validate(version)
                for version in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    def get_node_definition(
        self, *, slug: str, version: int | None = None
    ) -> NodeDefinitionResponse:
        node, node_version = self._service.get_node_by_slug(slug, version=version)
        return self._mapper.map_node_response(node, node_version)

    def get_node_definition_version(
        self, *, slug: str, version: int
    ) -> NodeDefinitionResponse:
        return self.get_node_definition(slug=slug, version=version)

    def list_workflow_definitions(
        self,
        *,
        pagination: PaginationParams,
        status: str | None = None,
        q: str | None = None,
    ) -> PageResult[WorkflowDefinitionSummary]:
        page = self._service.list_workflows_page(
            pagination.to_page_request(), status=status, q=q
        )
        return PageResult[WorkflowDefinitionSummary](
            items=[
                WorkflowDefinitionSummary.model_validate(workflow)
                for workflow in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    def list_workflow_definition_versions(
        self, *, slug: str, pagination: PaginationParams
    ) -> PageResult[WorkflowDefinitionVersionSummary]:
        page = self._service.list_workflow_versions_page(
            slug, pagination.to_page_request()
        )
        return PageResult[WorkflowDefinitionVersionSummary](
            items=[
                WorkflowDefinitionVersionSummary.model_validate(version)
                for version in page.items
            ],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    def get_workflow_definition(
        self, *, slug: str, version: int | None = None
    ) -> WorkflowDefinitionResponse:
        workflow, workflow_version = self._service.get_workflow_by_slug(
            slug, version=version
        )
        return self._mapper.map_workflow_response(workflow, workflow_version)

    def get_workflow_definition_version(
        self, *, slug: str, version: int
    ) -> WorkflowDefinitionResponse:
        return self.get_workflow_definition(slug=slug, version=version)
