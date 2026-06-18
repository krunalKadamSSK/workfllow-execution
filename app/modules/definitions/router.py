from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.application.definitions.ingest import DefinitionIngestService
from app.modules.definitions.schemas.base_types import BaseTypeResponse
from app.modules.definitions.schemas.nodes import NodeDefinitionIngest
from app.modules.definitions.schemas.responses import (
    NodeDefinitionResponse,
    NodeDefinitionSummary,
    NodeDefinitionVersionResponse,
    WorkflowDefinitionResponse,
    WorkflowDefinitionSummary,
    WorkflowDefinitionVersionResponse,
)
from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest

router = APIRouter(prefix="/definitions", tags=["definitions"])


@router.get("/base-types", response_model=list[BaseTypeResponse])
def list_base_types(
    session: Session = Depends(get_session),
) -> list[BaseTypeResponse]:
    service = DefinitionIngestService(session)
    return [BaseTypeResponse.model_validate(base_type) for base_type in service.list_base_types()]


def _node_response(node, version) -> NodeDefinitionResponse:
    return NodeDefinitionResponse(
        id=node.id,
        name=node.name,
        slug=node.slug,
        status=node.status,
        latest_version=node.latest_version,
        created_at=node.created_at,
        updated_at=node.updated_at,
        version=NodeDefinitionVersionResponse.model_validate(version),
    )


def _workflow_response(workflow, version) -> WorkflowDefinitionResponse:
    return WorkflowDefinitionResponse(
        id=workflow.id,
        name=workflow.name,
        slug=workflow.slug,
        status=workflow.status,
        latest_version=workflow.latest_version,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
        version=WorkflowDefinitionVersionResponse.model_validate(version),
    )


@router.post("/nodes", response_model=NodeDefinitionResponse, status_code=201)
def publish_node_definition(
    payload: NodeDefinitionIngest,
    session: Session = Depends(get_session),
) -> NodeDefinitionResponse:
    service = DefinitionIngestService(session)
    node, version = service.publish_node(payload)
    session.commit()
    return _node_response(node, version)


@router.get("/nodes", response_model=list[NodeDefinitionSummary])
def list_node_definitions(
    session: Session = Depends(get_session),
) -> list[NodeDefinitionSummary]:
    service = DefinitionIngestService(session)
    return [NodeDefinitionSummary.model_validate(node) for node in service.list_nodes()]


@router.get("/nodes/{slug}", response_model=NodeDefinitionResponse)
def get_node_definition(
    slug: str,
    version: int | None = None,
    session: Session = Depends(get_session),
) -> NodeDefinitionResponse:
    service = DefinitionIngestService(session)
    node, node_version = service.get_node_by_slug(slug, version=version)
    return _node_response(node, node_version)


@router.get("/nodes/{slug}/versions/{version}", response_model=NodeDefinitionResponse)
def get_node_definition_version(
    slug: str,
    version: int,
    session: Session = Depends(get_session),
) -> NodeDefinitionResponse:
    service = DefinitionIngestService(session)
    node, node_version = service.get_node_by_slug(slug, version=version)
    return _node_response(node, node_version)


@router.post("/workflows", response_model=WorkflowDefinitionResponse, status_code=201)
def publish_workflow_definition(
    payload: WorkflowDefinitionIngest,
    session: Session = Depends(get_session),
) -> WorkflowDefinitionResponse:
    service = DefinitionIngestService(session)
    workflow, version = service.publish_workflow(payload)
    session.commit()
    return _workflow_response(workflow, version)


@router.get("/workflows", response_model=list[WorkflowDefinitionSummary])
def list_workflow_definitions(
    session: Session = Depends(get_session),
) -> list[WorkflowDefinitionSummary]:
    service = DefinitionIngestService(session)
    return [
        WorkflowDefinitionSummary.model_validate(workflow) for workflow in service.list_workflows()
    ]


@router.get("/workflows/{slug}", response_model=WorkflowDefinitionResponse)
def get_workflow_definition(
    slug: str,
    version: int | None = None,
    session: Session = Depends(get_session),
) -> WorkflowDefinitionResponse:
    service = DefinitionIngestService(session)
    workflow, workflow_version = service.get_workflow_by_slug(slug, version=version)
    return _workflow_response(workflow, workflow_version)


@router.get("/workflows/{slug}/versions/{version}", response_model=WorkflowDefinitionResponse)
def get_workflow_definition_version(
    slug: str,
    version: int,
    session: Session = Depends(get_session),
) -> WorkflowDefinitionResponse:
    service = DefinitionIngestService(session)
    workflow, workflow_version = service.get_workflow_by_slug(slug, version=version)
    return _workflow_response(workflow, workflow_version)
