"""Memento builder: capture static task outputs from a prior workflow instance."""

from __future__ import annotations

from typing import Any

from app.domain.enums import ExecutionStatus
from app.domain.exceptions import NotFoundError, ValidationError
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.domain.seed.field_classifier import FieldSeedClassifier, StaticFieldClassifier
from app.infrastructure.persistence.models import WorkflowInstance, WorkflowNodeExecution
from app.patterns.executions.factories import NodeExecutorRegistry, get_default_registry


class SeedDefaultsMemento:
    """Memento of static field defaults keyed by workflow graph node id.

    Memento pattern — https://refactoring.guru/design-patterns/memento
    Captures prior revision state without exposing executor internals.
    """

    def __init__(self, defaults_by_node: dict[str, dict[str, Any]]) -> None:
        self._defaults_by_node = {
            node_id: dict(values) for node_id, values in defaults_by_node.items()
        }

    def to_storage(self) -> dict[str, dict[str, Any]]:
        return {
            node_id: dict(values) for node_id, values in self._defaults_by_node.items()
        }

    def for_node(self, workflow_node_id: str) -> dict[str, Any]:
        return dict(self._defaults_by_node.get(workflow_node_id) or {})

    @classmethod
    def empty(cls) -> SeedDefaultsMemento:
        return cls({})

    @classmethod
    def from_storage(cls, raw: dict[str, Any] | None) -> SeedDefaultsMemento:
        if not raw:
            return cls.empty()
        cleaned: dict[str, dict[str, Any]] = {}
        for node_id, values in raw.items():
            if isinstance(values, dict):
                cleaned[str(node_id)] = dict(values)
        return cls(cleaned)


class SeedDefaultsMementoBuilder:
    """Builds a seed memento from the latest completed executions of a source instance."""

    def __init__(
        self,
        *,
        instance_repository: InstanceRepository,
        definition_repository: DefinitionRepository,
        classifier: FieldSeedClassifier | None = None,
        executors: NodeExecutorRegistry | None = None,
    ) -> None:
        self._instances = instance_repository
        self._definitions = definition_repository
        self._classifier = classifier or StaticFieldClassifier()
        self._executors = executors or get_default_registry()

    def build(self, source_instance_id: str) -> SeedDefaultsMemento:
        source = self._instances.get_workflow_instance(source_instance_id)
        if source is None:
            raise NotFoundError(f"Seed source workflow instance not found: {source_instance_id}")

        node_instances = self._instances.list_node_instances(source_instance_id)
        node_by_id = {node.id: node for node in node_instances}
        latest = self._latest_completed_by_node(source_instance_id, node_by_id)
        versions_by_id = self._definitions.get_node_definition_versions_by_ids(
            {
                node.node_definition_version_id
                for node in node_instances
                if node.node_definition_version_id
            }
        )

        defaults_by_node: dict[str, dict[str, Any]] = {}
        for workflow_node_id, execution in latest.items():
            node_instance = next(
                (n for n in node_instances if n.workflow_node_id == workflow_node_id),
                None,
            )
            if node_instance is None:
                continue
            node_version = versions_by_id.get(node_instance.node_definition_version_id)
            if node_version is None:
                continue
            defaults_by_node[workflow_node_id] = self._static_defaults_for_definition(
                definition_json=node_version.definition_json,
                outputs=execution.outputs_json or {},
            )

        return SeedDefaultsMemento(defaults_by_node)

    def _latest_completed_by_node(
        self,
        workflow_instance_id: str,
        node_by_id: dict[str, Any],
    ) -> dict[str, WorkflowNodeExecution]:
        latest: dict[str, WorkflowNodeExecution] = {}
        for execution in self._instances.list_node_executions(workflow_instance_id):
            if execution.status != ExecutionStatus.COMPLETED:
                continue
            node_instance = node_by_id.get(execution.workflow_node_instance_id)
            if node_instance is None:
                continue
            current = latest.get(node_instance.workflow_node_id)
            if current is None or execution.execution_number > current.execution_number:
                latest[node_instance.workflow_node_id] = execution
        return latest

    def _static_defaults_for_definition(
        self,
        *,
        definition_json: dict[str, Any],
        outputs: dict[str, Any],
    ) -> dict[str, Any]:
        return self._executors.for_definition(definition_json).extract_seed_defaults(
            definition_json,
            outputs,
            classifier=self._classifier,
        )


def require_seed_source_compatible(
    *,
    source: WorkflowInstance,
    target_workflow_definition_id: str,
) -> None:
    if source.workflow_definition_id != target_workflow_definition_id:
        raise ValidationError(
            "seed_from_instance_id must reference an instance of the same workflow definition"
        )
