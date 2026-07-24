"""Shared pagination query models (API layer)."""

from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.application.common.dto.pagination import Page, PageRequest
from app.core.constants import DEFAULT_LIMIT, MAX_LIMIT

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Common limit/offset query parameters for list endpoints."""

    limit: int = Field(default=DEFAULT_LIMIT, ge=1, le=MAX_LIMIT)
    offset: int = Field(default=0, ge=0)

    def to_page_request(self) -> PageRequest:
        return PageRequest.create_page_request(limit=self.limit, offset=self.offset)


class PageMeta(BaseModel):
    total: int
    limit: int
    offset: int


class PageResult(BaseModel, Generic[T]):
    """List envelope for versioned list APIs."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    limit: int = DEFAULT_LIMIT
    offset: int = 0

    @classmethod
    def from_page(cls, page: Page[T]) -> PageResult[T]:
        return cls(
            items=list(page.items),
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )
