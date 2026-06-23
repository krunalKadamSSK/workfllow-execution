from __future__ import annotations

from collections import deque
from collections.abc import Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any, Literal

from app.domain.enums import NodeStatus

NodeKind = Literal["start", "task", "end"]


@dataclass(frozen=True)
class GraphInputBinding:
    input_key: str
    source_node_id: str
    output_key: str
    locked: bool = False

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GraphInputBinding:
        source = data.get("source", {})
        if source.get("kind") != "upstream":
            raise ValueError(f"Unsupported input source kind: {source.get('kind')}")
        return cls(
            input_key=str(data["inputKey"]),
            source_node_id=str(source["sourceNodeId"]),
            output_key=str(source["outputKey"]),
            locked=bool(data.get("locked", False)),
        )


@dataclass(frozen=True)
class GraphNode:
    id: str
    kind: NodeKind
    node_definition_id: str | None = None
    label: str | None = None
    inputs: tuple[GraphInputBinding, ...] = field(default_factory=tuple)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GraphNode:
        kind = data["kind"]
        if kind not in {"start", "task", "end"}:
            raise ValueError(f"Unsupported node kind: {kind}")

        raw_inputs = data.get("inputs") or []
        inputs = tuple(GraphInputBinding.from_dict(item) for item in raw_inputs)

        node_definition_id = data.get("nodeDefinitionId")
        if kind == "task" and not node_definition_id:
            raise ValueError(f"Task node '{data['id']}' must include nodeDefinitionId")

        label = data.get("label") or data.get("name")

        return cls(
            id=str(data["id"]),
            kind=kind,
            node_definition_id=str(node_definition_id) if node_definition_id else None,
            label=label if isinstance(label, str) and label else None,
            inputs=inputs,
        )

    @property
    def is_task(self) -> bool:
        return self.kind == "task"


@dataclass(frozen=True)
class GraphEdge:
    id: str
    source: str
    target: str

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> GraphEdge:
        return cls(
            id=str(data["id"]),
            source=str(data["source"]),
            target=str(data["target"]),
        )


@dataclass(frozen=True)
class WorkflowGraph:
    """Navigable workflow graph built from stored definition JSON."""

    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    description: str | None = None
    _nodes_by_id: dict[str, GraphNode] = field(init=False, repr=False)
    _adjacency: dict[str, tuple[str, ...]] = field(init=False, repr=False)
    _reverse_adjacency: dict[str, tuple[str, ...]] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_nodes_by_id", {node.id: node for node in self.nodes})

        forward: dict[str, list[str]] = {node.id: [] for node in self.nodes}
        reverse: dict[str, list[str]] = {node.id: [] for node in self.nodes}
        for edge in self.edges:
            if edge.source in forward:
                forward[edge.source].append(edge.target)
            if edge.target in reverse:
                reverse[edge.target].append(edge.source)

        object.__setattr__(
            self,
            "_adjacency",
            {node_id: tuple(targets) for node_id, targets in forward.items()},
        )
        object.__setattr__(
            self,
            "_reverse_adjacency",
            {node_id: tuple(sources) for node_id, sources in reverse.items()},
        )

    @classmethod
    def from_definition_json(cls, data: Mapping[str, Any]) -> WorkflowGraph:
        nodes = tuple(GraphNode.from_dict(node) for node in data.get("nodes", []))
        edges = tuple(GraphEdge.from_dict(edge) for edge in data.get("edges", []))
        return cls(
            description=data.get("description"),
            nodes=nodes,
            edges=edges,
        )

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes_by_id.get(node_id)

    def require_node(self, node_id: str) -> GraphNode:
        node = self.get_node(node_id)
        if node is None:
            raise KeyError(f"Workflow node not found: {node_id}")
        return node

    @property
    def start_node(self) -> GraphNode:
        starts = [node for node in self.nodes if node.kind == "start"]
        if len(starts) != 1:
            raise ValueError("Workflow graph must contain exactly one start node")
        return starts[0]

    @property
    def end_nodes(self) -> tuple[GraphNode, ...]:
        return tuple(node for node in self.nodes if node.kind == "end")

    @property
    def task_nodes(self) -> tuple[GraphNode, ...]:
        return tuple(node for node in self.nodes if node.kind == "task")

    def successors(self, node_id: str) -> tuple[str, ...]:
        return self._adjacency.get(node_id, ())

    def predecessors(self, node_id: str) -> tuple[str, ...]:
        return self._reverse_adjacency.get(node_id, ())

    def downstream_task_nodes(self, node_id: str) -> tuple[GraphNode, ...]:
        visited: set[str] = set()
        queue = deque(self.successors(node_id))
        task_nodes: list[GraphNode] = []

        while queue:
            current_id = queue.popleft()
            if current_id in visited:
                continue
            visited.add(current_id)

            node = self.require_node(current_id)
            if node.is_task:
                task_nodes.append(node)
            queue.extend(self.successors(current_id))

        return tuple(task_nodes)

    def next_pending_task_from(
        self,
        source_node_id: str,
        node_statuses: Mapping[str, NodeStatus],
    ) -> GraphNode | None:
        """First PENDING task reachable along outgoing edges from source_node_id."""
        visited: set[str] = set()

        def walk(node_id: str) -> GraphNode | None:
            for successor_id in self.successors(node_id):
                if successor_id in visited:
                    continue
                visited.add(successor_id)

                node = self.require_node(successor_id)
                if node.is_task:
                    if node_statuses.get(node.id) == NodeStatus.PENDING:
                        return node
                    continue

                found = walk(successor_id)
                if found is not None:
                    return found
            return None

        return walk(source_node_id)

    def topological_order(self) -> tuple[str, ...]:
        indegree = {node.id: len(self.predecessors(node.id)) for node in self.nodes}
        queue = deque(node_id for node_id, degree in indegree.items() if degree == 0)
        order: list[str] = []

        while queue:
            node_id = queue.popleft()
            order.append(node_id)
            for successor in self.successors(node_id):
                indegree[successor] -= 1
                if indegree[successor] == 0:
                    queue.append(successor)

        if len(order) != len(self.nodes):
            raise ValueError("Workflow graph contains a cycle")

        return tuple(order)

    def __iter__(self) -> Iterator[GraphNode]:
        return iter(self.nodes)
