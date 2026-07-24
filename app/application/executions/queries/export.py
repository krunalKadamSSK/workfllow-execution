"""Excel export queries."""

from __future__ import annotations

from collections.abc import Callable

from app.application.events.event_store import EventStore
from app.application.executions.batch_export import BatchInstanceExportService
from app.application.executions.export import (
    build_instance_excel_export,
    safe_export_filename,
)
from app.application.executions.queries.get_instance import GetInstanceStateQuery
from app.domain.graph.workflow_graph import WorkflowGraph
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.domain.ports.projection_repository import ProjectionRepositoryPort as ProjectionRepository
from app.infrastructure.persistence.models import WorkflowInstance


class ExportInstancesQuery:
    """Builds single- and all-instance Excel exports."""

    def __init__(
        self,
        *,
        definitions: DefinitionRepository,
        instances: InstanceRepository,
        projections: ProjectionRepository,
        events: EventStore,
        get_instance: GetInstanceStateQuery,
        load_graph: Callable[[WorkflowInstance], WorkflowGraph],
    ) -> None:
        self._definitions = definitions
        self._instances = instances
        self._projections = projections
        self._events = events
        self._get_instance = get_instance
        self._load_graph = load_graph

    def export_instance_excel(self, workflow_instance_id: str) -> tuple[bytes, str]:
        state = self._get_instance.get_instance_state(workflow_instance_id)
        instance = state["instance"]
        executions = self._instances.list_node_executions(workflow_instance_id)
        events = self._events.list_workflow_events(workflow_instance_id)
        workflow_definition = self._definitions.get_workflow_definition(
            instance.workflow_definition_id
        )
        content = build_instance_excel_export(
            instance=instance,
            state=state,
            executions=executions,
            events=events,
            workflow_definition_name=(
                workflow_definition.name if workflow_definition is not None else None
            ),
        )
        return content, f"{safe_export_filename(instance.name)}.xlsx"

    def export_all_instances_excel(self) -> tuple[bytes, str]:
        return BatchInstanceExportService(
            instances=self._instances,
            definitions=self._definitions,
            projections=self._projections,
            list_all_events=self._events.list_all_workflow_events,
            load_graph=self._load_graph,
        ).export_all_instances_excel()
