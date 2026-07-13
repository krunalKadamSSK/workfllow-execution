"""add table base type

Revision ID: 003_table_base_type
Revises: 002_base_types
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.infrastructure.db.seeds.base_types import BASE_TYPES_SEED

revision: str = "003_table_base_type"
down_revision: Union[str, Sequence[str], None] = "002_base_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE_ROW = next(row for row in BASE_TYPES_SEED if row["kind"] == "table")


def upgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text(
            """
            INSERT INTO base_types (id, kind, display_name, description, enabled, version)
            VALUES (:id, :kind, :display_name, :description, :enabled, :version)
            ON CONFLICT (kind) DO NOTHING
            """
        ),
        _TABLE_ROW,
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM base_types WHERE kind = 'table'"))
