"""Paginated / filtered node-execution log queries (JOIN batch reads)."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.application.common.dto.pagination import Page, PageRequest
from app.application.executions.definition_maps import load_node_definition_maps
from app.domain.enums import ExecutionStatus
from app.domain.graph.workflow_graph import WorkflowGraph
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.infrastructure.persistence.models import WorkflowInstance
from app.patterns.executions.helpers.task_names import build_task_names


class NodeExecutionLogQuery:
    """Builds execution log rows with a single JOIN round-trip per page."""

    def __init__(
        self,
        *,
        instances: InstanceRepository,
        definitions: DefinitionRepository,
        load_graph: Callable[[WorkflowInstance], WorkflowGraph],
    ) -> None:
        self._instances = instances
        self._definitions = definitions
        self._load_graph = load_graph

    def list_node_executions(self, workflow_instance_id: str) -> list[dict[str, Any]]:
        task_names = self._task_names_for(workflow_instance_id)
        return [
            self.map_execution_row(execution, node_instance, task_names)
            for execution, node_instance in self._instances.list_node_execution_rows(
                workflow_instance_id
            )
        ]

    def list_node_executions_page(
        self,
        workflow_instance_id: str,
        page: PageRequest,
        *,
        workflow_node_id: str | None = None,
        status: ExecutionStatus | None = None,
    ) -> Page[dict[str, Any]]:
        task_names = self._task_names_for(workflow_instance_id)
        joined = self._instances.list_node_executions_page(
            workflow_instance_id,
            page,
            workflow_node_id=workflow_node_id,
            status=status,
        )
        rows = [
            self.map_execution_row(execution, node_instance, task_names)
            for execution, node_instance in joined.items
        ]
        return Page.create_page(
            items=rows,
            total=joined.total,
            limit=joined.limit,
            offset=joined.offset,
        )

    def _task_names_for(self, workflow_instance_id: str) -> dict[str, str]:
        instance = self._instances.require_workflow_instance(workflow_instance_id)
        graph = self._load_graph(instance)
        node_instances = self._instances.list_node_instances(workflow_instance_id)
        definition_maps = load_node_definition_maps(
            self._definitions,
            node_instances,
            extra_definition_ids={
                node.node_definition_id
                for node in graph.task_nodes
                if node.node_definition_id is not None
            },
        )
        return build_task_names(
            graph=graph,
            node_instances=node_instances,
            definition_maps=definition_maps,
        )

    @staticmethod
    def map_execution_row(execution, node_instance, task_names: dict[str, str]) -> dict[str, Any]:
        return {
            "id": execution.id,
            "workflow_node_id": node_instance.workflow_node_id,
            "workflow_node_instance_id": execution.workflow_node_instance_id,
            "execution_number": execution.execution_number,
            "inputs_json": execution.inputs_json,
            "outputs_json": execution.outputs_json,
            "status": execution.status.value,
            "executed_by": execution.executed_by,
            "started_at": execution.started_at,
            "completed_at": execution.completed_at,
            "task_name": task_names.get(node_instance.workflow_node_id),
        }
