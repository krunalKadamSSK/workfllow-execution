"""add base_types catalog

Revision ID: 002_base_types
Revises: 4a780231d1ef
Create Date: 2026-06-18

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_base_types"
down_revision: Union[str, Sequence[str], None] = "4a780231d1ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BASE_TYPES_SEED = [
    {
        "id": "6a30f2cc1adf6e10e72bcf91",
        "kind": "userInput",
        "display_name": "User task",
        "description": "Form inputs filled at run time",
        "enabled": True,
        "version": "1",
    },
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
    op.bulk_insert(base_types, _BASE_TYPES_SEED)


def downgrade() -> None:
    op.drop_table("base_types")
