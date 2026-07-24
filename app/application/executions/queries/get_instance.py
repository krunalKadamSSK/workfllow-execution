"""Get instance state query (aggregate read model for API responses)."""

from __future__ import annotations

from typing import Any

from app.application.executions.definition_maps import load_node_definition_maps
from app.application.executions.graph_runtime import GraphRuntime
from app.application.executions.input_binder import GraphInputBinder
from app.application.executions.scheduler import GraphScheduler
from app.application.executions.upstream_resolver import UpstreamInputResolver
from app.domain.enums import NodeStatus
from app.domain.graph.workflow_graph import WorkflowGraph
from app.domain.ports.definition_repository import DefinitionRepositoryPort as DefinitionRepository
from app.domain.ports.executors import ExecutionContext
from app.domain.ports.instance_repository import InstanceRepositoryPort as InstanceRepository
from app.domain.ports.projection_repository import ProjectionRepositoryPort as ProjectionRepository
from app.infrastructure.executions.projection_reader import PrefetchedNodeProjectionReader
from app.infrastructure.persistence.models import WorkflowNodeInstance
from app.patterns.executions.builders.seed_memento import SeedDefaultsMemento
from app.patterns.executions.factories import NodeExecutorRegistry
from app.patterns.executions.helpers.summary import build_execution_summary
from app.patterns.executions.helpers.task_names import build_task_names, resolve_task_name


class GetInstanceStateQuery:
    """Builds the full instance state payload used by HTTP responses."""

    def __init__(
        self,
        *,
        definitions: DefinitionRepository,
        instances: InstanceRepository,
        projections: ProjectionRepository,
        executors: NodeExecutorRegistry,
        runtime: GraphRuntime,
    ) -> None:
        self._definitions = definitions
        self._instances = instances
        self._projections = projections
        self._executors = executors
        self._runtime = runtime

    def get_instance_state(
        self,
        workflow_instance_id: str,
        *,
        after_task_id: str | None = None,
    ) -> dict[str, Any]:
        instance = self._instances.require_workflow_instance(workflow_instance_id)
        node_instances = self._instances.list_node_instances(workflow_instance_id)
        workflow_state = self._projections.get_workflow_state(workflow_instance_id)
        graph = self._runtime.load_graph(instance)
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
        next_task_id = self._resolve_next_task_id(
            graph, node_instances, after_task_id=after_task_id
        )
        return {
            "instance": instance,
            "node_instances": node_instances,
            "workflow_projection": workflow_state,
            "execution_summary": build_execution_summary(
                graph=graph,
                workflow_projection=workflow_state,
                node_instances=node_instances,
                task_names=task_names,
                definition_maps=definition_maps,
            ),
            "task_names": task_names,
            "next_task_id": next_task_id,
            "next_task_name": task_names.get(next_task_id) if next_task_id else None,
            "pending_node_forms": self._prepare_pending_node_forms(
                workflow_instance_id,
                node_instances,
                graph,
                definition_maps=definition_maps,
            ),
        }

    def _resolve_next_task_id(
        self,
        graph: WorkflowGraph,
        node_instances: list[WorkflowNodeInstance],
        *,
        after_task_id: str | None,
    ) -> str | None:
        statuses = {node.workflow_node_id: node.status for node in node_instances}
        anchor = after_task_id or self._anchor_node_id(graph, node_instances)
        return GraphScheduler(graph).resolve_next_task_id(statuses, from_node_id=anchor)

    @staticmethod
    def _anchor_node_id(graph: WorkflowGraph, node_instances: list[WorkflowNodeInstance]) -> str:
        completed = [node for node in node_instances if node.status == NodeStatus.COMPLETED]
        if not completed:
            return graph.start_node.id

        topo_index = {node_id: index for index, node_id in enumerate(graph.topological_order())}
        latest = max(
            completed,
            key=lambda node: topo_index.get(node.workflow_node_id, -1),
        )
        return latest.workflow_node_id

    def _prepare_pending_node_forms(
        self,
        workflow_instance_id: str,
        node_instances: list[WorkflowNodeInstance],
        graph: WorkflowGraph,
        *,
        definition_maps=None,
    ) -> dict[str, dict[str, Any]]:
        pending_forms: dict[str, dict[str, Any]] = {}
        instance = self._instances.require_workflow_instance(workflow_instance_id)
        seed_memento = SeedDefaultsMemento.from_storage(instance.seed_defaults_json)

        maps = definition_maps or load_node_definition_maps(self._definitions, node_instances)
        statuses_by_graph_id = {node.workflow_node_id: node.status for node in node_instances}
        input_binder = GraphInputBinder(
            UpstreamInputResolver(
                PrefetchedNodeProjectionReader(
                    values_by_graph_id=self._projections.get_node_values_map_for_instance(
                        workflow_instance_id
                    ),
                    statuses_by_graph_id=statuses_by_graph_id,
                )
            )
        )

        for node_instance in node_instances:
            if node_instance.status != NodeStatus.PENDING:
                continue

            graph_node = graph.require_node(node_instance.workflow_node_id)
            node_version = maps.versions_by_id.get(node_instance.node_definition_version_id)
            if node_version is None:
                continue

            definition_json = node_version.definition_json
            resolved_inputs = input_binder.resolve(
                workflow_instance_id=workflow_instance_id,
                graph_node=graph_node,
            )
            executor = self._executors.for_definition(definition_json)
            context = ExecutionContext(
                workflow_instance_id=workflow_instance_id,
                workflow_node_instance_id=node_instance.id,
                workflow_node_id=node_instance.workflow_node_id,
                node_definition_version_id=node_instance.node_definition_version_id,
                base_kind=executor.base_kind,
                definition_json=definition_json,
                resolved_inputs=resolved_inputs.values,
                locked_input_keys=resolved_inputs.locked_keys,
                execution_number=node_instance.current_execution,
                seed_defaults=seed_memento.for_node(node_instance.workflow_node_id),
            )
            node_definition = (
                maps.definitions_by_id.get(graph_node.node_definition_id)
                if graph_node.node_definition_id
                else None
            )
            pending_forms[node_instance.workflow_node_id] = {
                "task_name": resolve_task_name(
                    graph_node=graph_node,
                    definition_json=definition_json,
                    definition_name=node_definition.name if node_definition else None,
                ),
                **executor.prepare_pending_node_form(context),
            }

        return pending_forms
