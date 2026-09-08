"""add configTable base type

Revision ID: 007_config_table_base_type
Revises: 006_search_list_indexes
Create Date: 2026-09-08

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_config_table_base_type"
down_revision: Union[str, Sequence[str], None] = "006_search_list_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CONFIG_TABLE_ROW = {
    "id": "6a30f2cc1adf6e10e72bcf95",
    "kind": "configTable",
    "display_name": "Config table task",
    "description": "Load configuration DB rows, edit with Synapse fields, aggregations",
    "enabled": True,
    "version": "1",
}


def upgrade() -> None:
    bind = op.get_bind()
    existing = bind.execute(
        sa.text("SELECT 1 FROM base_types WHERE kind = :kind"),
        {"kind": "configTable"},
    ).first()
    if existing:
        bind.execute(
            sa.text(
                """
                UPDATE base_types
                SET display_name = :display_name,
                    description = :description,
                    enabled = :enabled,
                    version = :version
                WHERE kind = :kind
                """
            ),
            _CONFIG_TABLE_ROW,
        )
        return

    base_types = sa.table(
        "base_types",
        sa.column("id", sa.String),
        sa.column("kind", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("version", sa.String),
    )
    op.bulk_insert(base_types, [_CONFIG_TABLE_ROW])


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM base_types WHERE kind = 'configTable'"))
