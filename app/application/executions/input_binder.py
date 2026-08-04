from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from app.domain.exceptions import InputResolutionError
from app.domain.graph.workflow_graph import GraphNode
from app.domain.ports.executors import InputResolver


@dataclass(frozen=True)
class ResolvedNodeInputs:
    values: dict[str, Any]
    locked_keys: frozenset[str]


class GraphInputBinder:
    """Resolves workflow graph input bindings from upstream outputs or instance metadata."""

    def __init__(self, input_resolver: InputResolver) -> None:
        self._input_resolver = input_resolver

    def resolve(
        self,
        *,
        workflow_instance_id: str,
        graph_node: GraphNode,
        instance_metadata: Mapping[str, Any] | None = None,
    ) -> ResolvedNodeInputs:
        values: dict[str, Any] = {}
        locked_keys: set[str] = set()
        metadata = instance_metadata or {}

        for binding in graph_node.inputs:
            if binding.kind == "metadata":
                key = binding.metadata_key or ""
                if key not in metadata:
                    raise InputResolutionError(
                        f"Instance metadata has no key '{key}' for input "
                        f"'{binding.input_key}' on node '{graph_node.id}'"
                    )
                value = metadata[key]
            else:
                if not binding.source_node_id or not binding.output_key:
                    raise InputResolutionError(
                        f"Upstream binding for input '{binding.input_key}' on node "
                        f"'{graph_node.id}' is missing sourceNodeId/outputKey"
                    )
                value = self._input_resolver.resolve(
                    workflow_instance_id=workflow_instance_id,
                    source_node_id=binding.source_node_id,
                    output_key=binding.output_key,
                )
            values[binding.input_key] = value
            if binding.locked:
                locked_keys.add(binding.input_key)

        return ResolvedNodeInputs(values=values, locked_keys=frozenset(locked_keys))
