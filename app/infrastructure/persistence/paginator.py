"""SQLAlchemy query pagination helper (implements ``QueryPaginator``)."""

from __future__ import annotations

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.application.common.dto.pagination import Page, PageRequest


class SqlAlchemyQueryPaginator:
    """Applies LIMIT/OFFSET and counts matching rows for list queries."""

    def apply_pagination(self, statement: Select, page: PageRequest) -> Select:
        return statement.limit(page.limit).offset(page.offset)

    def count_rows(self, session: Session, statement: Select) -> int:
        count_statement = select(func.count()).select_from(
            statement.order_by(None).subquery()
        )
        return int(session.scalar(count_statement) or 0)

    def fetch_page(
        self,
        session: Session,
        statement: Select,
        page: PageRequest,
    ) -> Page:
        total = self.count_rows(session, statement)
        rows = list(session.scalars(self.apply_pagination(statement, page)))
        return Page.create_page(
            items=rows,
            total=total,
            limit=page.limit,
            offset=page.offset,
        )

    def fetch_page_rows(
        self,
        session: Session,
        statement: Select,
        page: PageRequest,
    ) -> Page:
        """Paginate multi-column / joined result rows (``session.execute``)."""
        total = self.count_rows(session, statement)
        rows = list(session.execute(self.apply_pagination(statement, page)).all())
        return Page.create_page(
            items=rows,
            total=total,
            limit=page.limit,
            offset=page.offset,
        )
