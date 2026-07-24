"""Application-layer pagination DTOs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

from app.core.constants import DEFAULT_LIMIT, MAX_LIMIT

T = TypeVar("T")


class PageRequest:
    """Validated limit/offset for list queries."""

    def __init__(self, *, limit: int = DEFAULT_LIMIT, offset: int = 0) -> None:
        if limit < 1 or limit > MAX_LIMIT:
            raise ValueError(f"limit must be between 1 and {MAX_LIMIT}")
        if offset < 0:
            raise ValueError("offset must be >= 0")
        self.limit = limit
        self.offset = offset

    @classmethod
    def create_page_request(
        cls, *, limit: int | None = None, offset: int | None = None
    ) -> PageRequest:
        return cls(
            limit=DEFAULT_LIMIT if limit is None else limit,
            offset=0 if offset is None else offset,
        )


@dataclass(frozen=True)
class Page(Generic[T]):
    """Paginated result used by application services."""

    items: list[T]
    total: int
    limit: int
    offset: int

    @classmethod
    def create_page(
        cls,
        *,
        items: list[T],
        total: int,
        limit: int,
        offset: int,
    ) -> Page[T]:
        return cls(items=items, total=total, limit=limit, offset=offset)
