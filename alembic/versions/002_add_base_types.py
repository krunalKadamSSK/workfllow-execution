"""add base_types catalog

Revision ID: 002_base_types
Revises: 4a780231d1ef
Create Date: 2026-06-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.infrastructure.db.seeds.base_types import BASE_TYPES_SEED

revision: str = "002_base_types"
down_revision: Union[str, Sequence[str], None] = "4a780231d1ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    base_types = op.create_table(
        "base_types",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("display_name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("kind"),
    )
    op.bulk_insert(base_types, BASE_TYPES_SEED)


def downgrade() -> None:
    op.drop_table("base_types")
