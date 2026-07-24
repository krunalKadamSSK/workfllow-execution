"""HTTP API schemas (versioned under v1/)."""

from app.api.schemas.common.errors import ApiErrorBody, ApiErrorResponse
from app.api.schemas.common.pagination import PageMeta, PageResult, PaginationParams

__all__ = [
    "ApiErrorBody",
    "ApiErrorResponse",
    "PageMeta",
    "PageResult",
    "PaginationParams",
]
