"""Definition write controller — command actions (no session.commit)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.api.controllers.definitions.response_mapper import DefinitionHttpResponseMapper
from app.api.controllers.interfaces import DefinitionResponseMapper
from app.api.schemas.v1.definitions.nodes import NodeDefinitionIngest
from app.api.schemas.v1.definitions.responses import (
    NodeDefinitionResponse,
    WorkflowDefinitionResponse,
)
from app.api.schemas.v1.definitions.workflows import WorkflowDefinitionIngest
from app.application.definitions.ingest import DefinitionIngestService


class DefinitionHttpCommandController:
    """Implements ``DefinitionCommandController`` Protocol."""

    def __init__(
        self,
        *,
        session: Session,
        mapper: DefinitionResponseMapper | None = None,
    ) -> None:
        self._service = DefinitionIngestService(session)
        self._mapper = mapper or DefinitionHttpResponseMapper()

    def publish_node_definition(
        self, payload: NodeDefinitionIngest
    ) -> NodeDefinitionResponse:
        node, version = self._service.publish_node(payload)
        return self._mapper.map_node_response(node, version)

    def publish_workflow_definition(
        self, payload: WorkflowDefinitionIngest
    ) -> WorkflowDefinitionResponse:
        workflow, version = self._service.publish_workflow(payload)
        return self._mapper.map_workflow_response(workflow, version)
