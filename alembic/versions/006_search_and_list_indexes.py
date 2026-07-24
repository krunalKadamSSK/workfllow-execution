"""add search and list indexes for instances, events, executions

Revision ID: 006_search_list_indexes
Revises: 005_instance_metadata_seed
Create Date: 2026-07-24

"""

from typing import Sequence, Union

from app.infrastructure.persistence.indexes import AlembicIndexMigrator

revision: str = "006_search_list_indexes"
down_revision: Union[str, Sequence[str], None] = "005_instance_metadata_seed"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    AlembicIndexMigrator().upgrade_indexes()


def downgrade() -> None:
    AlembicIndexMigrator().downgrade_indexes()
