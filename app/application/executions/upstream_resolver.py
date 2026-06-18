from __future__ import annotations

from typing import Any

from app.domain.exceptions import InputResolutionError
from app.domain.ports.projections import NodeProjectionReader


class UpstreamInputResolver:
    """Resolves upstream task outputs from node projections."""

    def __init__(self, projection_reader: NodeProjectionReader) -> None:
        self._projection_reader = projection_reader

    def resolve(
        self,
        *,
        workflow_instance_id: str,
        source_node_id: str,
        output_key: str,
    ) -> Any:
        values = self._projection_reader.get_node_values(
            workflow_instance_id=workflow_instance_id,
            workflow_node_id=source_node_id,
        )
        if values is None:
            raise InputResolutionError(
                f"Upstream node '{source_node_id}' has no projection for instance "
                f"'{workflow_instance_id}'"
            )
        if output_key not in values:
            raise InputResolutionError(
                f"Upstream node '{source_node_id}' has no output key '{output_key}'"
            )
        return values[output_key]
