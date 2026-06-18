from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.database import get_db


def get_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")
