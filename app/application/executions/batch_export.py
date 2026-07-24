"""Batch export of all workflow instances (Phase 6 — no per-instance N+1)."""

from __future__ import annotations

from typing import Any

from app.application.executions.definition_maps import load_node_definition_maps
from app.application.executions.export import (
    ALL_EXPORT_FILENAME,
    InstanceExportContext,
    build_all_instances_excel_export,
)
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.domain.ports.projection_repository import ProjectionRepositoryPort as ProjectionRepository
from app.infrastructure.persistence.models import WorkflowInstance
from app.patterns.executions.helpers.summary import build_execution_summary
from app.patterns.executions.helpers.task_names import build_task_names


class BatchInstanceExportService:
    """Builds the all-instances Excel export with batched reads."""

    def __init__(
        self,
        *,
        instances: InstanceRepository,
        definitions: DefinitionRepository,
        projections: ProjectionRepository,
        list_all_events,
        load_graph,
    ) -> None:
        self._instances = instances
        self._definitions = definitions
        self._projections = projections
        self._list_all_events = list_all_events
        self._load_graph = load_graph

    def export_all_instances_excel(self) -> tuple[bytes, str]:
        instances = self._instances.list_workflow_instances()
        instance_ids = [instance.id for instance in instances]

        executions_by_instance: dict[str, list] = {}
        for execution in self._instances.list_all_node_executions():
            executions_by_instance.setdefault(execution.workflow_instance_id, []).append(
                execution
            )

        events_by_instance: dict[str, list] = {}
        for event in self._list_all_events():
            events_by_instance.setdefault(event.workflow_instance_id, []).append(event)

        nodes_by_instance = self._batch_node_instances(instance_ids)
        projections_by_instance = self._batch_workflow_projections(instance_ids)

        definition_ids = {instance.workflow_definition_id for instance in instances}
        definitions_by_id = self._definitions.get_workflow_definitions_by_ids(definition_ids)
        workflow_names = {
            definition_id: definition.name
            for definition_id, definition in definitions_by_id.items()
        }
        for definition_id in definition_ids:
            workflow_names.setdefault(definition_id, None)

        contexts: list[InstanceExportContext] = []
        for instance in instances:
            state = self._build_export_state(
                instance=instance,
                node_instances=nodes_by_instance.get(instance.id, []),
                workflow_projection=projections_by_instance.get(instance.id),
            )
            contexts.append(
                InstanceExportContext(
                    instance=instance,
                    state=state,
                    executions=executions_by_instance.get(instance.id, []),
                    events=events_by_instance.get(instance.id, []),
                    workflow_definition_name=workflow_names[instance.workflow_definition_id],
                )
            )

        return build_all_instances_excel_export(contexts), ALL_EXPORT_FILENAME

    def _batch_node_instances(
        self, instance_ids: list[str]
    ) -> dict[str, list]:
        if not instance_ids:
            return {}
        grouped: dict[str, list] = {instance_id: [] for instance_id in instance_ids}
        for node in self._instances.list_all_node_instances():
            if node.workflow_instance_id in grouped:
                grouped[node.workflow_instance_id].append(node)
        return grouped

    def _batch_workflow_projections(self, instance_ids: list[str]) -> dict[str, dict | None]:
        return self._projections.get_workflow_states_for_instances(instance_ids)

    def _build_export_state(
        self,
        *,
        instance: WorkflowInstance,
        node_instances: list,
        workflow_projection: dict | None,
    ) -> dict[str, Any]:
        graph = self._load_graph(instance)
        definition_maps = load_node_definition_maps(
            self._definitions,
            node_instances,
            extra_definition_ids={
                node.node_definition_id
                for node in graph.task_nodes
                if node.node_definition_id is not None
            },
        )
        task_names = build_task_names(
            graph=graph,
            node_instances=node_instances,
            definition_maps=definition_maps,
        )
        return {
            "instance": instance,
            "node_instances": node_instances,
            "workflow_projection": workflow_projection,
            "execution_summary": build_execution_summary(
                graph=graph,
                workflow_projection=workflow_projection,
                node_instances=node_instances,
                task_names=task_names,
                definition_maps=definition_maps,
            ),
            "task_names": task_names,
            "next_task_id": None,
            "next_task_name": None,
            "pending_node_forms": {},
        }
