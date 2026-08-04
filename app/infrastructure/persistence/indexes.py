"""Named search/list indexes (ADR-002 Phase 3)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class IndexSpec:
    """Single database index definition for migrations."""

    name: str
    table_name: str
    columns: tuple[str, ...]


@runtime_checkable
class IndexCatalog(Protocol):
    def list_index_specs(self) -> tuple[IndexSpec, ...]: ...


class SearchListIndexCatalog:
    """Indexes that accelerate RFQ lists, event logs, and execution logs."""

    def list_index_specs(self) -> tuple[IndexSpec, ...]:
        return (
            IndexSpec(
                name="ix_workflow_node_executions_instance_started",
                table_name="workflow_node_executions",
                columns=("workflow_instance_id", "started_at"),
            ),
            IndexSpec(
                name="ix_workflow_node_projections_instance_id",
                table_name="workflow_node_projections",
                columns=("workflow_instance_id",),
            ),
            IndexSpec(
                name="ix_workflow_instances_created_at",
                table_name="workflow_instances",
                columns=("created_at",),
            ),
            IndexSpec(
                name="ix_workflow_instances_status_created",
                table_name="workflow_instances",
                columns=("status", "created_at"),
            ),
            IndexSpec(
                name="ix_workflow_instances_definition_id",
                table_name="workflow_instances",
                columns=("workflow_definition_id",),
            ),
            IndexSpec(
                name="ix_workflow_instances_definition_version_id",
                table_name="workflow_instances",
                columns=("workflow_definition_version_id",),
            ),
            IndexSpec(
                name="ix_workflow_events_instance_type_seq",
                table_name="workflow_events",
                columns=("workflow_instance_id", "event_type", "sequence_number"),
            ),
        )


class AlembicIndexMigrator:
    """Applies or rolls back ``IndexCatalog`` specs via Alembic operations."""

    def __init__(self, catalog: IndexCatalog | None = None) -> None:
        self._catalog = catalog or SearchListIndexCatalog()

    def list_index_specs(self) -> tuple[IndexSpec, ...]:
        return self._catalog.list_index_specs()

    def upgrade_indexes(self) -> None:
        from alembic import op

        for spec in self.list_index_specs():
            op.create_index(spec.name, spec.table_name, list(spec.columns), unique=False)

    def downgrade_indexes(self) -> None:
        from alembic import op

        for spec in reversed(self.list_index_specs()):
            op.drop_index(spec.name, table_name=spec.table_name)
