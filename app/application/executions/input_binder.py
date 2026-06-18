from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.graph.workflow_graph import GraphNode
from app.domain.ports.executors import InputResolver


@dataclass(frozen=True)
class ResolvedNodeInputs:
    values: dict[str, Any]
    locked_keys: frozenset[str]


class GraphInputBinder:
    """Resolves workflow graph input bindings via an InputResolver."""

    def __init__(self, input_resolver: InputResolver) -> None:
        self._input_resolver = input_resolver

    def resolve(
        self,
        *,
        workflow_instance_id: str,
        graph_node: GraphNode,
    ) -> ResolvedNodeInputs:
        values: dict[str, Any] = {}
        locked_keys: set[str] = set()

        for binding in graph_node.inputs:
            value = self._input_resolver.resolve(
                workflow_instance_id=workflow_instance_id,
                source_node_id=binding.source_node_id,
                output_key=binding.output_key,
            )
            values[binding.input_key] = value
            if binding.locked:
                locked_keys.add(binding.input_key)

        return ResolvedNodeInputs(values=values, locked_keys=frozenset(locked_keys))
