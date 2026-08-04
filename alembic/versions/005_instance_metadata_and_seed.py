"""add instance metadata, rfq_id index, and seed defaults

Revision ID: 005_instance_metadata_seed
Revises: 004_sync_base_types
Create Date: 2026-07-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_instance_metadata_seed"
down_revision: Union[str, Sequence[str], None] = "004_sync_base_types"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workflow_instances",
        sa.Column(
            "instance_metadata",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.add_column(
        "workflow_instances",
        sa.Column("rfq_id", sa.String(), nullable=True),
    )
    op.add_column(
        "workflow_instances",
        sa.Column(
            "seed_defaults_json",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'{}'::json"),
        ),
    )
    op.create_index(
        "ix_workflow_instances_rfq_id",
        "workflow_instances",
        ["rfq_id"],
    )
    op.create_index(
        "ix_workflow_instances_rfq_id_status",
        "workflow_instances",
        ["rfq_id", "status"],
    )


def downgrade() -> None:
    op.drop_index("ix_workflow_instances_rfq_id_status", table_name="workflow_instances")
    op.drop_index("ix_workflow_instances_rfq_id", table_name="workflow_instances")
    op.drop_column("workflow_instances", "seed_defaults_json")
    op.drop_column("workflow_instances", "rfq_id")
    op.drop_column("workflow_instances", "instance_metadata")
