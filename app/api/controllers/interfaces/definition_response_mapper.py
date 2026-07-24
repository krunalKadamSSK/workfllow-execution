from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.api.schemas.v1.definitions.responses import (
    NodeDefinitionResponse,
    WorkflowDefinitionResponse,
)


@runtime_checkable
class DefinitionResponseMapper(Protocol):
    def map_node_response(self, node: object, version: object) -> NodeDefinitionResponse: ...

    def map_workflow_response(
        self, workflow: object, version: object
    ) -> WorkflowDefinitionResponse: ...
