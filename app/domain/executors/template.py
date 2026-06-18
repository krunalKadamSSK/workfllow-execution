from __future__ import annotations

import re
from typing import Any

from app.domain.exceptions import InputResolutionError

_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([a-zA-Z_][\w]*)\s*\}\}")


def substitute_templates(template: str, values: dict[str, Any]) -> str:
    """Replace {{variable}} placeholders using resolved field values."""

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values or values[key] is None:
            raise InputResolutionError(
                f"Cannot substitute template variable '{key}' in '{template}'"
            )
        return str(values[key])

    return _TEMPLATE_PATTERN.sub(replace, template)
