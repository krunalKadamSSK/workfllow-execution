"""Facade repository combining node + workflow definition persistence."""

from app.infrastructure.persistence.repositories.node_definitions import NodeDefinitionRepository
from app.infrastructure.persistence.repositories.workflow_definitions import (
    WorkflowDefinitionRepository,
)


class DefinitionRepository(NodeDefinitionRepository, WorkflowDefinitionRepository):
    """Single entry point used by application services (action methods inherited)."""

    pass
