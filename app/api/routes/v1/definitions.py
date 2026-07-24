"""Definition routes — validation and DI only."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.controllers.interfaces import (
    DefinitionCommandController,
    DefinitionQueryController,
)
from app.api.deps import (
    get_definition_command_controller,
    get_definition_query_controller,
    get_pagination_params,
)
from app.api.schemas.common.pagination import PageResult, PaginationParams
from app.api.schemas.v1.definitions.base_types import BaseTypeResponse
from app.api.schemas.v1.definitions.nodes import NodeDefinitionIngest
from app.api.schemas.v1.definitions.responses import (
    NodeDefinitionResponse,
    NodeDefinitionSummary,
    NodeDefinitionVersionSummary,
    WorkflowDefinitionResponse,
    WorkflowDefinitionSummary,
    WorkflowDefinitionVersionSummary,
)
from app.api.schemas.v1.definitions.workflows import WorkflowDefinitionIngest

router = APIRouter(prefix="/definitions", tags=["definitions"])


@router.get("/base-types", response_model=list[BaseTypeResponse])
def list_base_types(
    controller: DefinitionQueryController = Depends(get_definition_query_controller),
) -> list[BaseTypeResponse]:
    return controller.list_base_types()


@router.post("/nodes", response_model=NodeDefinitionResponse, status_code=201)
def publish_node_definition(
    payload: NodeDefinitionIngest,
    controller: DefinitionCommandController = Depends(get_definition_command_controller),
) -> NodeDefinitionResponse:
    return controller.publish_node_definition(payload)


@router.get("/nodes", response_model=PageResult[NodeDefinitionSummary])
def list_node_definitions(
    status: str | None = Query(None),
    q: str | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination_params),
    controller: DefinitionQueryController = Depends(get_definition_query_controller),
) -> PageResult[NodeDefinitionSummary]:
    return controller.list_node_definitions(
        pagination=pagination, status=status, q=q
    )


@router.get(
    "/nodes/{slug}/versions",
    response_model=PageResult[NodeDefinitionVersionSummary],
)
def list_node_definition_versions(
    slug: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    controller: DefinitionQueryController = Depends(get_definition_query_controller),
) -> PageResult[NodeDefinitionVersionSummary]:
    return controller.list_node_definition_versions(slug=slug, pagination=pagination)


@router.get("/nodes/{slug}", response_model=NodeDefinitionResponse)
def get_node_definition(
    slug: str,
    version: int | None = None,
    controller: DefinitionQueryController = Depends(get_definition_query_controller),
) -> NodeDefinitionResponse:
    return controller.get_node_definition(slug=slug, version=version)


@router.get("/nodes/{slug}/versions/{version}", response_model=NodeDefinitionResponse)
def get_node_definition_version(
    slug: str,
    version: int,
    controller: DefinitionQueryController = Depends(get_definition_query_controller),
) -> NodeDefinitionResponse:
    return controller.get_node_definition_version(slug=slug, version=version)


@router.post("/workflows", response_model=WorkflowDefinitionResponse, status_code=201)
def publish_workflow_definition(
    payload: WorkflowDefinitionIngest,
    controller: DefinitionCommandController = Depends(get_definition_command_controller),
) -> WorkflowDefinitionResponse:
    return controller.publish_workflow_definition(payload)


@router.get("/workflows", response_model=PageResult[WorkflowDefinitionSummary])
def list_workflow_definitions(
    status: str | None = Query(None),
    q: str | None = Query(None),
    pagination: PaginationParams = Depends(get_pagination_params),
    controller: DefinitionQueryController = Depends(get_definition_query_controller),
) -> PageResult[WorkflowDefinitionSummary]:
    return controller.list_workflow_definitions(
        pagination=pagination, status=status, q=q
    )


@router.get(
    "/workflows/{slug}/versions",
    response_model=PageResult[WorkflowDefinitionVersionSummary],
)
def list_workflow_definition_versions(
    slug: str,
    pagination: PaginationParams = Depends(get_pagination_params),
    controller: DefinitionQueryController = Depends(get_definition_query_controller),
) -> PageResult[WorkflowDefinitionVersionSummary]:
    return controller.list_workflow_definition_versions(
        slug=slug, pagination=pagination
    )


@router.get("/workflows/{slug}", response_model=WorkflowDefinitionResponse)
def get_workflow_definition(
    slug: str,
    version: int | None = None,
    controller: DefinitionQueryController = Depends(get_definition_query_controller),
) -> WorkflowDefinitionResponse:
    return controller.get_workflow_definition(slug=slug, version=version)


@router.get("/workflows/{slug}/versions/{version}", response_model=WorkflowDefinitionResponse)
def get_workflow_definition_version(
    slug: str,
    version: int,
    controller: DefinitionQueryController = Depends(get_definition_query_controller),
) -> WorkflowDefinitionResponse:
    return controller.get_workflow_definition_version(slug=slug, version=version)
