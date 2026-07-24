"""sync base_types seed catalog

Revision ID: 004_sync_base_types
Revises: 003_table_base_type
Create Date: 2026-07-03

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.infrastructure.persistence.seeds.base_types import BASE_TYPES_SEED

revision: str = "004_sync_base_types"
down_revision: Union[str, Sequence[str], None] = "003_table_base_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_REMOVED_BASE_TYPES = [
    {
        "id": "6a30f2cc1adf6e10e72bcf92",
        "kind": "ai",
        "display_name": "AI task",
        "description": "LLM step with model and API credentials",
        "enabled": True,
        "version": "1",
    },
    {
        "id": "6a30f2cc1adf6e10e72bcf93",
        "kind": "script",
        "display_name": "Script task",
        "description": "JavaScript logic with live testing in the designer",
        "enabled": True,
        "version": "1",
    },
]


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(sa.text("DELETE FROM base_types WHERE kind IN ('ai', 'script')"))
    for row in BASE_TYPES_SEED:
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
            row,
        )


def downgrade() -> None:
    bind = op.get_bind()
    base_types = sa.table(
        "base_types",
        sa.column("id", sa.String),
        sa.column("kind", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("version", sa.String),
    )
    op.bulk_insert(base_types, _REMOVED_BASE_TYPES)
    bind.execute(
        sa.text(
            """
            UPDATE base_types
            SET description = :description
            WHERE kind = 'table'
            """
        ),
        {"description": "Dynamic row collection filled at run time"},
    )
