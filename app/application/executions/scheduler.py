from __future__ import annotations

from app.domain.enums import NodeStatus
from app.domain.graph.workflow_graph import GraphNode, WorkflowGraph


class GraphScheduler:
    """Determines which task nodes are ready based on upstream completion."""

    def __init__(self, graph: WorkflowGraph) -> None:
        self._graph = graph

    def predecessors_satisfied(
        self, node_id: str, completed_task_node_ids: set[str]
    ) -> bool:
        for predecessor_id in self._graph.predecessors(node_id):
            predecessor = self._graph.require_node(predecessor_id)
            if predecessor.kind == "task" and predecessor_id not in completed_task_node_ids:
                return False
        return True

    def ready_task_nodes(
        self, node_statuses: dict[str, NodeStatus]
    ) -> list[GraphNode]:
        completed = {
            node_id
            for node_id, status in node_statuses.items()
            if status == NodeStatus.COMPLETED
        }
        ready: list[GraphNode] = []
        for node in self._graph.task_nodes:
            status = node_statuses.get(node.id, NodeStatus.WAITING)
            if status not in {NodeStatus.WAITING, NodeStatus.INVALIDATED}:
                continue
            if self.predecessors_satisfied(node.id, completed):
                ready.append(node)
        return ready

    def all_tasks_completed(self, node_statuses: dict[str, NodeStatus]) -> bool:
        return all(
            node_statuses.get(node.id) == NodeStatus.COMPLETED
            for node in self._graph.task_nodes
        )

    def resolve_next_task_id(
        self,
        node_statuses: dict[str, NodeStatus],
        *,
        from_node_id: str,
    ) -> str | None:
        next_task = self._graph.next_pending_task_from(from_node_id, node_statuses)
        return next_task.id if next_task is not None else None

    def downstream_task_nodes(self, node_id: str) -> tuple[GraphNode, ...]:
        return self._graph.downstream_task_nodes(node_id)
