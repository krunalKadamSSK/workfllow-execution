from app.api.schemas.common.pagination import PageResult, PaginationParams
from app.application.common.dto.pagination import Page, PageRequest
from app.core.constants import DEFAULT_LIMIT, MAX_LIMIT
from app.infrastructure.persistence.paginator import SqlAlchemyQueryPaginator


def test_page_request_create_page_request_defaults() -> None:
    page = PageRequest.create_page_request()
    assert page.limit == DEFAULT_LIMIT
    assert page.offset == 0


def test_page_request_rejects_invalid_limit() -> None:
    try:
        PageRequest(limit=MAX_LIMIT + 1, offset=0)
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "limit" in str(exc)


def test_pagination_params_to_page_request() -> None:
    params = PaginationParams(limit=10, offset=20)
    request = params.to_page_request()
    assert request.limit == 10
    assert request.offset == 20


def test_page_result_from_page() -> None:
    page = Page.create_page(items=["a", "b"], total=2, limit=10, offset=0)
    result = PageResult[str].from_page(page)
    assert result.items == ["a", "b"]
    assert result.total == 2
    assert result.limit == 10
    assert result.offset == 0


def test_sqlalchemy_query_paginator_apply_pagination() -> None:
    from sqlalchemy import column, select

    statement = select(column("id"))
    page = PageRequest(limit=5, offset=15)
    paginated = SqlAlchemyQueryPaginator().apply_pagination(statement, page)
    compiled = str(paginated.compile(compile_kwargs={"literal_binds": True}))
    assert "LIMIT 5" in compiled.upper()
    assert "OFFSET 15" in compiled.upper()
