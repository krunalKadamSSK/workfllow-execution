from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

from sqlalchemy.orm import Session
from sqlalchemy.sql import Select

from app.application.common.dto.pagination import Page, PageRequest

T = TypeVar("T")


@runtime_checkable
class QueryPaginator(Protocol):
    def apply_pagination(self, statement: Select, page: PageRequest) -> Select: ...

    def count_rows(self, session: Session, statement: Select) -> int: ...

    def fetch_page(
        self,
        session: Session,
        statement: Select,
        page: PageRequest,
    ) -> Page: ...
