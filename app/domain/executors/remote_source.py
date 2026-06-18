from __future__ import annotations

from typing import Any

from app.domain.executors.template import substitute_templates


def prepare_remote_source(field: dict[str, Any], values: dict[str, Any]) -> dict[str, str] | None:
    """Prepare remoteSource metadata with template-substituted URL (no HTTP fetch)."""
    remote_source = field.get("remoteSource")
    if not remote_source:
        return None

    url = substitute_templates(str(remote_source["url"]), values)
    return {
        "url": url,
        "resultPath": str(remote_source["resultPath"]),
    }
