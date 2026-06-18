from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.domain.exceptions import DuplicateSlugError, NotFoundError
from app.infrastructure.db.models import (
    NodeDefinition,
    NodeDefinitionVersion,
    WorkflowDefinition,
    WorkflowDefinitionVersion,
)
from app.infrastructure.db.repositories.base import BaseRepository


class DefinitionRepository(BaseRepository):
    def create_node_definition(
        self,
        *,
        name: str,
        slug: str,
        status: str,
        definition_json: dict,
        definition_id: str | None = None,
        created_by: str | None = None,
    ) -> tuple[NodeDefinition, NodeDefinitionVersion]:
        node = NodeDefinition(
            id=definition_id or str(uuid4()),
            name=name,
            slug=slug,
            status=status,
            latest_version=1,
        )
        version = NodeDefinitionVersion(
            node_definition_id=node.id,
            version=1,
            definition_json=definition_json,
            created_by=created_by,
        )
        self.session.add(node)
        self.session.add(version)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DuplicateSlugError(f"Node definition slug already exists: {slug}") from exc
        return node, version

    def publish_node_version(
        self,
        *,
        node_definition_id: str,
        definition_json: dict,
        created_by: str | None = None,
    ) -> NodeDefinitionVersion:
        node = self.session.get(NodeDefinition, node_definition_id)
        if node is None:
            raise NotFoundError(f"Node definition not found: {node_definition_id}")

        next_version = node.latest_version + 1
        version = NodeDefinitionVersion(
            node_definition_id=node.id,
            version=next_version,
            definition_json=definition_json,
            created_by=created_by,
        )
        node.latest_version = next_version
        self.session.add(version)
        self.session.flush()
        return version

    def get_node_definition_by_slug(self, slug: str) -> NodeDefinition | None:
        return self.session.scalar(select(NodeDefinition).where(NodeDefinition.slug == slug))

    def get_node_definition(self, definition_id: str) -> NodeDefinition | None:
        return self.session.get(NodeDefinition, definition_id)

    def get_node_definition_version(
        self, node_definition_id: str, version: int
    ) -> NodeDefinitionVersion | None:
        return self.session.scalar(
            select(NodeDefinitionVersion).where(
                NodeDefinitionVersion.node_definition_id == node_definition_id,
                NodeDefinitionVersion.version == version,
            )
        )

    def get_node_definition_version_by_id(self, version_id: str) -> NodeDefinitionVersion | None:
        return self.session.get(NodeDefinitionVersion, version_id)

    def create_workflow_definition(
        self,
        *,
        name: str,
        slug: str,
        status: str,
        definition_json: dict,
        definition_id: str | None = None,
        created_by: str | None = None,
    ) -> tuple[WorkflowDefinition, WorkflowDefinitionVersion]:
        workflow = WorkflowDefinition(
            id=definition_id or str(uuid4()),
            name=name,
            slug=slug,
            status=status,
            latest_version=1,
        )
        version = WorkflowDefinitionVersion(
            workflow_definition_id=workflow.id,
            version=1,
            definition_json=definition_json,
            created_by=created_by,
        )
        self.session.add(workflow)
        self.session.add(version)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise DuplicateSlugError(f"Workflow definition slug already exists: {slug}") from exc
        return workflow, version

    def publish_workflow_version(
        self,
        *,
        workflow_definition_id: str,
        definition_json: dict,
        created_by: str | None = None,
    ) -> WorkflowDefinitionVersion:
        workflow = self.session.get(WorkflowDefinition, workflow_definition_id)
        if workflow is None:
            raise NotFoundError(f"Workflow definition not found: {workflow_definition_id}")

        next_version = workflow.latest_version + 1
        version = WorkflowDefinitionVersion(
            workflow_definition_id=workflow.id,
            version=next_version,
            definition_json=definition_json,
            created_by=created_by,
        )
        workflow.latest_version = next_version
        self.session.add(version)
        self.session.flush()
        return version

    def get_workflow_definition_by_slug(self, slug: str) -> WorkflowDefinition | None:
        return self.session.scalar(
            select(WorkflowDefinition).where(WorkflowDefinition.slug == slug)
        )

    def get_workflow_definition(self, definition_id: str) -> WorkflowDefinition | None:
        return self.session.get(WorkflowDefinition, definition_id)

    def get_workflow_definition_version(
        self, workflow_definition_id: str, version: int
    ) -> WorkflowDefinitionVersion | None:
        return self.session.scalar(
            select(WorkflowDefinitionVersion).where(
                WorkflowDefinitionVersion.workflow_definition_id == workflow_definition_id,
                WorkflowDefinitionVersion.version == version,
            )
        )

    def get_workflow_definition_version_by_id(
        self, version_id: str
    ) -> WorkflowDefinitionVersion | None:
        return self.session.get(WorkflowDefinitionVersion, version_id)

    def pin_workflow_version(
        self, workflow_definition_id: str, version: int | None = None
    ) -> WorkflowDefinitionVersion:
        workflow = self.get_workflow_definition(workflow_definition_id)
        if workflow is None:
            raise NotFoundError(f"Workflow definition not found: {workflow_definition_id}")

        target_version = version if version is not None else workflow.latest_version
        pinned = self.get_workflow_definition_version(workflow_definition_id, target_version)
        if pinned is None:
            raise NotFoundError(
                f"Workflow definition version not found: {workflow_definition_id} v{target_version}"
            )
        return pinned

    def pin_node_version(
        self, node_definition_id: str, version: int | None = None
    ) -> NodeDefinitionVersion:
        node = self.get_node_definition(node_definition_id)
        if node is None:
            raise NotFoundError(f"Node definition not found: {node_definition_id}")

        target_version = version if version is not None else node.latest_version
        pinned = self.get_node_definition_version(node_definition_id, target_version)
        if pinned is None:
            raise NotFoundError(
                f"Node definition version not found: {node_definition_id} v{target_version}"
            )
        return pinned
