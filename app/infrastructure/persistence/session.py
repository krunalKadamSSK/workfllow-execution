"""SQLAlchemy session manager (implements ``SessionManager``)."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, settings


class SqlAlchemySessionManager:
    """Owns the engine and session factory for the application."""

    def __init__(self, app_settings: Settings | None = None) -> None:
        cfg = app_settings or settings
        self._engine: Engine = create_engine(
            cfg.DATABASE_URL,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            connect_args={"connect_timeout": 5},
        )
        self._session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self._engine,
        )

    @property
    def engine(self) -> Engine:
        return self._engine

    def create_session(self) -> Session:
        return self._session_factory()

    def provide_session(self) -> Generator[Session, None, None]:
        session = self.create_session()
        try:
            yield session
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def check_connection(self) -> None:
        with self._engine.connect() as connection:
            connection.execute(text("SELECT 1"))


_session_manager: SqlAlchemySessionManager | None = None


def get_session_manager() -> SqlAlchemySessionManager:
    """Return the process-wide session manager (lazy singleton)."""
    global _session_manager
    if _session_manager is None:
        # Import models so mappers register on first use.
        import app.infrastructure.persistence.models  # noqa: F401

        _session_manager = SqlAlchemySessionManager()
    return _session_manager


def reset_session_manager() -> None:
    """Test helper — clear the singleton."""
    global _session_manager
    _session_manager = None
