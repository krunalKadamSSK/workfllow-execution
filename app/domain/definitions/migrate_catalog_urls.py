"""Rewrite hardcoded Synapse catalog hosts to root-relative paths.

Stored node blueprints previously baked ``VITE_CONFIG_API_BASE_URL`` into
``remoteSource.url`` / ``remoteOptions.url``. Relative paths let the frontend
config API client supply the host from env.
"""

from __future__ import annotations

import re
from copy import deepcopy
from typing import Any
from urllib.parse import urlsplit

_ABS_HTTP = re.compile(r"^https?://", re.IGNORECASE)
_REMOTE_KEYS = ("remoteSource", "remoteOptions")


def migrate_synapse_url_template(url: str) -> str:
    """Strip scheme+host from an absolute catalog URL template."""
    trimmed = url.strip()
    if not trimmed or trimmed.startswith("/"):
        return trimmed
    if not _ABS_HTTP.match(trimmed):
        return trimmed

    try:
        parts = urlsplit(trimmed)
    except ValueError:
        return trimmed

    path = parts.path or "/"
    if ".." in path:
        return trimmed
    if parts.query:
        return f"{path}?{parts.query}"
    return path


def _migrate_remote_block(remote: Any) -> bool:
    if not isinstance(remote, dict):
        return False
    url = remote.get("url")
    if not isinstance(url, str):
        return False
    next_url = migrate_synapse_url_template(url)
    if next_url == url:
        return False
    remote["url"] = next_url
    return True


def migrate_synapse_field(field: Any) -> bool:
    if not isinstance(field, dict):
        return False
    changed = False
    for key in _REMOTE_KEYS:
        if key in field and _migrate_remote_block(field.get(key)):
            changed = True
    return changed


def migrate_synapse_fields(fields: Any) -> bool:
    if not isinstance(fields, list):
        return False
    changed = False
    for field in fields:
        if migrate_synapse_field(field):
            changed = True
    return changed


def migrate_node_definition_json(definition: dict[str, Any]) -> dict[str, Any] | None:
    """
    Return a migrated copy of ``definition_json`` when URLs change; otherwise None.
    """
    doc = deepcopy(definition)
    changed = False

    form = doc.get("form")
    if isinstance(form, dict):
        if migrate_synapse_fields(form.get("fields")):
            changed = True

    table = doc.get("table")
    if isinstance(table, dict):
        if migrate_synapse_fields(table.get("headerFields")):
            changed = True
        if migrate_synapse_fields(table.get("columns")):
            changed = True

    config_table = doc.get("configTable")
    if isinstance(config_table, dict):
        if migrate_synapse_fields(config_table.get("queryInputs")):
            changed = True
        if migrate_synapse_fields(config_table.get("extraColumns")):
            changed = True
        mappings = config_table.get("columnMappings")
        if isinstance(mappings, list):
            for row in mappings:
                if not isinstance(row, dict):
                    continue
                if migrate_synapse_field(row.get("field")):
                    changed = True

    return doc if changed else None
