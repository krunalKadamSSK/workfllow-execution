from __future__ import annotations

from dataclasses import dataclass

from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.infrastructure.persistence.models import NodeDefinition, NodeDefinitionVersion
from app.infrastructure.persistence.models.instances import WorkflowNodeInstance


@dataclass(frozen=True)
class NodeDefinitionMaps:
    versions_by_id: dict[str, NodeDefinitionVersion]
    definitions_by_id: dict[str, NodeDefinition]


def load_node_definition_maps(
    definition_repository: DefinitionRepository,
    node_instances: list[WorkflowNodeInstance],
    *,
    extra_definition_ids: set[str] | None = None,
) -> NodeDefinitionMaps:
    """Batch-load node definition versions and parent definitions for instance nodes."""
    version_ids = {
        node.node_definition_version_id
        for node in node_instances
        if node.node_definition_version_id
    }
    versions_by_id = definition_repository.get_node_definition_versions_by_ids(version_ids)

    definition_ids = {version.node_definition_id for version in versions_by_id.values()}
    if extra_definition_ids:
        definition_ids.update(extra_definition_ids)

    definitions_by_id = definition_repository.get_node_definitions_by_ids(definition_ids)
    return NodeDefinitionMaps(
        versions_by_id=versions_by_id,
        definitions_by_id=definitions_by_id,
    )
