from sqlalchemy.orm import Session

from app.domain.exceptions import DuplicateSlugError, NotFoundError, ValidationError
from app.domain.validation.pipeline import validate_workflow_definition
from app.infrastructure.db.models import (
    NodeDefinition,
    NodeDefinitionVersion,
    WorkflowDefinition,
    WorkflowDefinitionVersion,
)
from app.infrastructure.db.repositories.definitions import DefinitionRepository
from app.modules.definitions.schemas.nodes import NodeDefinitionIngest
from app.modules.definitions.schemas.workflows import WorkflowDefinitionIngest


class DefinitionIngestService:
    def __init__(self, session: Session) -> None:
        self._repo = DefinitionRepository(session)

    def publish_node(
        self,
        payload: NodeDefinitionIngest,
        *,
        created_by: str | None = None,
    ) -> tuple[NodeDefinition, NodeDefinitionVersion]:
        existing = self._repo.get_node_definition(payload.id)
        if existing is not None:
            return self._publish_existing_node(existing, payload, created_by=created_by)

        slug_owner = self._repo.get_node_definition_by_slug(payload.slug)
        if slug_owner is not None:
            raise DuplicateSlugError(f"Node definition slug already exists: {payload.slug}")

        return self._repo.create_node_definition(
            definition_id=payload.id,
            name=payload.name,
            slug=payload.slug,
            status=payload.status,
            definition_json=payload.to_stored_json(),
            created_by=created_by,
        )

    def publish_workflow(
        self,
        payload: WorkflowDefinitionIngest,
        *,
        created_by: str | None = None,
    ) -> tuple[WorkflowDefinition, WorkflowDefinitionVersion]:
        published_node_ids, node_output_fields = self._resolve_task_node_definitions(payload)
        issues = validate_workflow_definition(
            payload,
            published_node_ids=published_node_ids,
            node_output_fields=node_output_fields,
        )
        if issues:
            raise ValidationError(
                "Workflow definition validation failed",
                details=[issue.to_dict() for issue in issues],
            )

        existing = self._repo.get_workflow_definition(payload.id)
        if existing is not None:
            return self._publish_existing_workflow(existing, payload, created_by=created_by)

        slug_owner = self._repo.get_workflow_definition_by_slug(payload.slug)
        if slug_owner is not None:
            raise DuplicateSlugError(f"Workflow definition slug already exists: {payload.slug}")

        return self._repo.create_workflow_definition(
            definition_id=payload.id,
            name=payload.name,
            slug=payload.slug,
            status=payload.status,
            definition_json=payload.to_stored_json(),
            created_by=created_by,
        )

    def get_node_by_slug(
        self, slug: str, *, version: int | None = None
    ) -> tuple[NodeDefinition, NodeDefinitionVersion]:
        node = self._repo.get_node_definition_by_slug(slug)
        if node is None:
            raise NotFoundError(f"Node definition not found: {slug}")

        target_version = version if version is not None else node.latest_version
        node_version = self._repo.get_node_definition_version(node.id, target_version)
        if node_version is None:
            raise NotFoundError(f"Node definition version not found: {slug} v{target_version}")

        return node, node_version

    def get_workflow_by_slug(
        self, slug: str, *, version: int | None = None
    ) -> tuple[WorkflowDefinition, WorkflowDefinitionVersion]:
        workflow = self._repo.get_workflow_definition_by_slug(slug)
        if workflow is None:
            raise NotFoundError(f"Workflow definition not found: {slug}")

        target_version = version if version is not None else workflow.latest_version
        workflow_version = self._repo.get_workflow_definition_version(workflow.id, target_version)
        if workflow_version is None:
            raise NotFoundError(f"Workflow definition version not found: {slug} v{target_version}")

        return workflow, workflow_version

    def list_nodes(self) -> list[NodeDefinition]:
        return self._repo.list_node_definitions()

    def list_workflows(self) -> list[WorkflowDefinition]:
        return self._repo.list_workflow_definitions()

    def _publish_existing_node(
        self,
        existing: NodeDefinition,
        payload: NodeDefinitionIngest,
        *,
        created_by: str | None = None,
    ) -> tuple[NodeDefinition, NodeDefinitionVersion]:
        if existing.slug != payload.slug:
            slug_owner = self._repo.get_node_definition_by_slug(payload.slug)
            if slug_owner is not None and slug_owner.id != existing.id:
                raise DuplicateSlugError(f"Node definition slug already exists: {payload.slug}")

        existing.name = payload.name
        existing.slug = payload.slug
        existing.status = payload.status

        version = self._repo.publish_node_version(
            node_definition_id=existing.id,
            definition_json=payload.to_stored_json(),
            created_by=created_by,
        )
        return existing, version

    def _publish_existing_workflow(
        self,
        existing: WorkflowDefinition,
        payload: WorkflowDefinitionIngest,
        *,
        created_by: str | None = None,
    ):
        if existing.slug != payload.slug:
            slug_owner = self._repo.get_workflow_definition_by_slug(payload.slug)
            if slug_owner is not None and slug_owner.id != existing.id:
                raise DuplicateSlugError(f"Workflow definition slug already exists: {payload.slug}")

        existing.name = payload.name
        existing.slug = payload.slug
        existing.status = payload.status

        version = self._repo.publish_workflow_version(
            workflow_definition_id=existing.id,
            definition_json=payload.to_stored_json(),
            created_by=created_by,
        )
        return existing, version

    def _resolve_task_node_definitions(
        self, payload: WorkflowDefinitionIngest
    ) -> tuple[set[str], dict[str, set[str]]]:
        published_node_ids: set[str] = set()
        node_output_fields: dict[str, set[str]] = {}

        for node in payload.task_nodes():
            assert node.nodeDefinitionId is not None
            definition = self._repo.get_node_definition(node.nodeDefinitionId)
            if definition is None or definition.status != "published":
                continue

            published_node_ids.add(definition.id)
            version = self._repo.get_node_definition_version(
                definition.id, definition.latest_version
            )
            if version is None:
                continue

            fields = version.definition_json.get("form", {}).get("fields", [])
            node_output_fields[definition.id] = {
                field["id"] for field in fields if isinstance(field, dict) and "id" in field
            }

        return published_node_ids, node_output_fields
