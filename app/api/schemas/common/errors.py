from typing import Any

from pydantic import BaseModel, Field


class ApiErrorBody(BaseModel):
    code: str
    message: str
    details: list[Any] = Field(default_factory=list)
    request_id: str | None = None


class ApiErrorResponse(BaseModel):
    error: ApiErrorBody
