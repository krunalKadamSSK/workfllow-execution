"""Port: base-type catalog persistence."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class BaseTypeRepositoryPort(Protocol):
    def require_enabled_kind(self, kind: str) -> Any: ...

    def list_base_types(self, *, enabled_only: bool = False) -> list[Any]: ...
