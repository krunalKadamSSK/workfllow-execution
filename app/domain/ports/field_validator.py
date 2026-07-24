"""Port: validates a single form field value."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FieldValidator(Protocol):
    def validate(
        self,
        *,
        field_id: str,
        field_definition: dict[str, Any],
        value: Any,
    ) -> None: ...
