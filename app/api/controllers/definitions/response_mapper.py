"""Concrete mapper: definition ORM rows → HTTP schemas."""

from __future__ import annotations

from app.api.schemas.v1.definitions.responses import (
    NodeDefinitionResponse,
    NodeDefinitionVersionResponse,
    WorkflowDefinitionResponse,
    WorkflowDefinitionVersionResponse,
)


class DefinitionHttpResponseMapper:
    """Implements ``DefinitionResponseMapper``."""

    def map_node_response(self, node: object, version: object) -> NodeDefinitionResponse:
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

    def map_workflow_response(
        self, workflow: object, version: object
    ) -> WorkflowDefinitionResponse:
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
