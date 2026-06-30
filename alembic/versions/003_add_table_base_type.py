"""add table base type

Revision ID: 003_table_base_type
Revises: 002_base_types
Create Date: 2026-06-24

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_table_base_type"
down_revision: Union[str, Sequence[str], None] = "002_base_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE_BASE_TYPE = {
    "id": "6a30f2cc1adf6e10e72bcf94",
    "kind": "table",
    "display_name": "Table task",
    "description": "Dynamic row collection filled at run time",
    "enabled": True,
    "version": "1",
}


def upgrade() -> None:
    op.execute(
        sa.text(
            """
            INSERT INTO base_types (id, kind, display_name, description, enabled, version)
            VALUES (:id, :kind, :display_name, :description, :enabled, :version)
            ON CONFLICT (kind) DO NOTHING
            """
        ).bindparams(**_TABLE_BASE_TYPE)
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM base_types WHERE kind = 'table'"))
