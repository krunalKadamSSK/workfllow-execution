from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.api.schemas.v1.definitions.nodes import NodeDefinitionIngest
from app.api.schemas.v1.definitions.responses import (
    NodeDefinitionResponse,
    WorkflowDefinitionResponse,
)
from app.api.schemas.v1.definitions.workflows import WorkflowDefinitionIngest


@runtime_checkable
class DefinitionCommandController(Protocol):
    def publish_node_definition(
        self, payload: NodeDefinitionIngest
    ) -> NodeDefinitionResponse: ...

    def publish_workflow_definition(
        self, payload: WorkflowDefinitionIngest
    ) -> WorkflowDefinitionResponse: ...
