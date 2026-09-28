"""strip hardcoded hosts from synapse catalog urls in node definitions

Revision ID: 008_migrate_catalog_urls
Revises: 007_config_table_base_type
Create Date: 2026-09-28

"""

from __future__ import annotations

import json
from typing import Any, Sequence, Union

import sqlalchemy as sa
from alembic import op

from app.domain.definitions.migrate_catalog_urls import migrate_node_definition_json

revision: str = "008_migrate_catalog_urls"
down_revision: Union[str, Sequence[str], None] = "007_config_table_base_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _as_dict(value: Any) -> dict[str, Any] | None:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None
    return None


def upgrade() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, definition_json FROM node_definition_versions")
    ).mappings()

    for row in rows:
        doc = _as_dict(row["definition_json"])
        if doc is None:
            continue
        migrated = migrate_node_definition_json(doc)
        if migrated is None:
            continue
        bind.execute(
            sa.text(
                """
                UPDATE node_definition_versions
                SET definition_json = CAST(:definition_json AS json)
                WHERE id = :id
                """
            ),
            {
                "id": row["id"],
                "definition_json": json.dumps(migrated, separators=(",", ":")),
            },
        )


def downgrade() -> None:
    # Hosts cannot be restored without knowing the original config API base.
    pass
