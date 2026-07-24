from __future__ import annotations

from typing import Protocol, runtime_checkable

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


@runtime_checkable
class DefinitionQueryController(Protocol):
    def list_base_types(self) -> list[BaseTypeResponse]: ...

    def list_node_definitions(
        self,
        *,
        pagination: PaginationParams,
        status: str | None = None,
        q: str | None = None,
    ) -> PageResult[NodeDefinitionSummary]: ...

    def list_node_definition_versions(
        self, *, slug: str, pagination: PaginationParams
    ) -> PageResult[NodeDefinitionVersionSummary]: ...

    def get_node_definition(
        self, *, slug: str, version: int | None = None
    ) -> NodeDefinitionResponse: ...

    def get_node_definition_version(
        self, *, slug: str, version: int
    ) -> NodeDefinitionResponse: ...

    def list_workflow_definitions(
        self,
        *,
        pagination: PaginationParams,
        status: str | None = None,
        q: str | None = None,
    ) -> PageResult[WorkflowDefinitionSummary]: ...

    def list_workflow_definition_versions(
        self, *, slug: str, pagination: PaginationParams
    ) -> PageResult[WorkflowDefinitionVersionSummary]: ...

    def get_workflow_definition(
        self, *, slug: str, version: int | None = None
    ) -> WorkflowDefinitionResponse: ...

    def get_workflow_definition_version(
        self, *, slug: str, version: int
    ) -> WorkflowDefinitionResponse: ...
