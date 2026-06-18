from __future__ import annotations

from dataclasses import dataclass

from app.domain.graph.workflow_graph import WorkflowGraph
from app.infrastructure.db.models import (
    WorkflowDefinitionVersion,
    WorkflowInstance,
    WorkflowNodeInstance,
)
from app.infrastructure.db.repositories.definitions import DefinitionRepository
from app.infrastructure.db.repositories.instances import InstanceRepository


@dataclass(frozen=True)
class BuiltWorkflowInstance:
    instance: WorkflowInstance
    workflow_version: WorkflowDefinitionVersion
    graph: WorkflowGraph
    node_instances: dict[str, WorkflowNodeInstance]


class WorkflowInstanceBuilder:
    """Builder for workflow instances and pinned task node rows."""

    def __init__(
        self,
        *,
        definition_repository: DefinitionRepository,
        instance_repository: InstanceRepository,
    ) -> None:
        self._definitions = definition_repository
        self._instances = instance_repository

    def build(
        self,
        *,
        name: str,
        workflow_definition_id: str,
        version: int | None = None,
        created_by: str | None = None,
    ) -> BuiltWorkflowInstance:
        workflow_version = self._definitions.pin_workflow_version(
            workflow_definition_id, version=version
        )
        graph = WorkflowGraph.from_definition_json(workflow_version.definition_json)

        instance = self._instances.create_workflow_instance(
            name=name,
            workflow_definition_id=workflow_definition_id,
            workflow_definition_version_id=workflow_version.id,
            created_by=created_by,
        )

        node_instances: dict[str, WorkflowNodeInstance] = {}
        for task_node in graph.task_nodes:
            assert task_node.node_definition_id is not None
            node_version = self._definitions.pin_node_version(task_node.node_definition_id)
            node_instance = self._instances.create_node_instance(
                workflow_instance_id=instance.id,
                workflow_node_id=task_node.id,
                node_definition_version_id=node_version.id,
            )
            node_instances[task_node.id] = node_instance

        return BuiltWorkflowInstance(
            instance=instance,
            workflow_version=workflow_version,
            graph=graph,
            node_instances=node_instances,
        )
