from sqlalchemy.orm import Session

from app.api.schemas.v1.definitions.nodes import NodeDefinitionIngest
from app.api.schemas.v1.definitions.workflows import WorkflowDefinitionIngest
from app.application.common.dto.pagination import Page, PageRequest
from app.domain.definitions.output_fields import (
    collect_input_field_ids,
    collect_output_field_ids,
)
from app.domain.exceptions import DuplicateSlugError, NotFoundError, ValidationError
from app.domain.ports.base_type_repository import BaseTypeRepositoryPort as BaseTypeRepository
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.validation.pipeline import validate_workflow_definition
from app.infrastructure.persistence.models import (
    NodeDefinition,
    NodeDefinitionVersion,
    WorkflowDefinition,
    WorkflowDefinitionVersion,
)
from app.infrastructure.persistence.models.base_types import BaseType
from app.patterns.executions.factories import NodeExecutorRegistry, get_default_registry


class DefinitionIngestService:
    def __init__(
        self,
        session: Session,
        *,
        executors: NodeExecutorRegistry | None = None,
    ) -> None:
        self._session = session
        self._repo = DefinitionRepository(session)
        self._base_types = BaseTypeRepository(session)
        self._executors = executors or get_default_registry()

    def _commit(self) -> None:
        self._session.commit()

    def publish_node(
        self,
        payload: NodeDefinitionIngest,
        *,
        created_by: str | None = None,
    ) -> tuple[NodeDefinition, NodeDefinitionVersion]:
        self._base_types.require_enabled_kind(payload.baseKind)

        stored = payload.to_stored_json()
        issues = self._executors.for_definition(stored).validate_definition(stored)
        if issues:
            raise ValidationError(
                "Node definition validation failed",
                details=[issue.to_dict() for issue in issues],
            )

        existing = self._repo.get_node_definition(payload.id)
        if existing is not None:
            result = self._publish_existing_node(existing, payload, created_by=created_by)
            self._commit()
            return result

        slug_owner = self._repo.get_node_definition_by_slug(payload.slug)
        if slug_owner is not None:
            raise DuplicateSlugError(f"Node definition slug already exists: {payload.slug}")

        result = self._repo.create_node_definition(
            definition_id=payload.id,
            name=payload.name,
            slug=payload.slug,
            status=payload.status,
            definition_json=payload.to_stored_json(),
            created_by=created_by,
        )
        self._commit()
        return result

    def publish_workflow(
        self,
        payload: WorkflowDefinitionIngest,
        *,
        created_by: str | None = None,
    ) -> tuple[WorkflowDefinition, WorkflowDefinitionVersion]:
        slug = payload.required_slug
        published_node_ids, node_output_fields, node_input_fields = (
            self._resolve_task_node_fields(payload)
        )
        issues = validate_workflow_definition(
            payload,
            published_node_ids=published_node_ids,
            node_output_fields=node_output_fields,
            node_input_fields=node_input_fields,
        )
        if issues:
            raise ValidationError(
                "Workflow definition validation failed",
                details=[issue.to_dict() for issue in issues],
            )

        existing = self._repo.get_workflow_definition(payload.id)
        if existing is not None:
            result = self._publish_existing_workflow(existing, payload, created_by=created_by)
            self._commit()
            return result

        slug_owner = self._repo.get_workflow_definition_by_slug(slug)
        if slug_owner is not None:
            raise DuplicateSlugError(f"Workflow definition slug already exists: {slug}")

        result = self._repo.create_workflow_definition(
            definition_id=payload.id,
            name=payload.name,
            slug=slug,
            status=payload.status,
            definition_json=payload.to_stored_json(),
            created_by=created_by,
        )
        self._commit()
        return result

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

    def list_nodes_page(
        self,
        page: PageRequest,
        *,
        status: str | None = None,
        q: str | None = None,
    ) -> Page[NodeDefinition]:
        return self._repo.list_node_definitions_page(page, status=status, q=q)

    def list_node_versions_page(
        self, slug: str, page: PageRequest
    ) -> Page[NodeDefinitionVersion]:
        node = self._repo.get_node_definition_by_slug(slug)
        if node is None:
            raise NotFoundError(f"Node definition not found: {slug}")
        return self._repo.list_node_versions_page(node.id, page)

    def list_workflows(self) -> list[WorkflowDefinition]:
        return self._repo.list_workflow_definitions()

    def list_workflows_page(
        self,
        page: PageRequest,
        *,
        status: str | None = None,
        q: str | None = None,
    ) -> Page[WorkflowDefinition]:
        return self._repo.list_workflow_definitions_page(page, status=status, q=q)

    def list_workflow_versions_page(
        self, slug: str, page: PageRequest
    ) -> Page[WorkflowDefinitionVersion]:
        workflow = self._repo.get_workflow_definition_by_slug(slug)
        if workflow is None:
            raise NotFoundError(f"Workflow definition not found: {slug}")
        return self._repo.list_workflow_versions_page(workflow.id, page)

    def list_base_types(self, *, enabled_only: bool = True) -> list[BaseType]:
        return self._base_types.list_base_types(enabled_only=enabled_only)

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
        slug = payload.required_slug
        if existing.slug != slug:
            slug_owner = self._repo.get_workflow_definition_by_slug(slug)
            if slug_owner is not None and slug_owner.id != existing.id:
                raise DuplicateSlugError(f"Workflow definition slug already exists: {slug}")

        existing.name = payload.name
        existing.slug = slug
        existing.status = payload.status

        version = self._repo.publish_workflow_version(
            workflow_definition_id=existing.id,
            definition_json=payload.to_stored_json(),
            created_by=created_by,
        )
        return existing, version

    def _resolve_task_node_fields(
        self, payload: WorkflowDefinitionIngest
    ) -> tuple[set[str], dict[str, set[str]], dict[str, set[str]]]:
        definition_ids = {
            node.nodeDefinitionId
            for node in payload.task_nodes()
            if node.nodeDefinitionId is not None
        }
        resolved = self._repo.get_published_node_definitions_with_latest_versions(definition_ids)

        published_node_ids: set[str] = set()
        node_output_fields: dict[str, set[str]] = {}
        node_input_fields: dict[str, set[str]] = {}

        for definition_id, (_definition, version) in resolved.items():
            published_node_ids.add(definition_id)
            node_output_fields[definition_id] = collect_output_field_ids(version.definition_json)
            node_input_fields[definition_id] = collect_input_field_ids(version.definition_json)

        return published_node_ids, node_output_fields, node_input_fields
