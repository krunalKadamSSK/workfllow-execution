import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

import app.infrastructure.db.models  # noqa: F401
from app.core.config import settings
from app.infrastructure.db.base import Base
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _database_available() -> bool:
    try:
        engine = create_engine(
            settings.DATABASE_URL,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 2},
        )
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


def pytest_collection_modifyitems(config, items) -> None:
    if _database_available():
        return
    skip = pytest.mark.skip(
        reason="PostgreSQL is not available; start docker-compose for integration tests"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip)


requires_database = pytest.mark.integration


@pytest.fixture(scope="session")
def db_engine():
    engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db_session(db_engine) -> Session:
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, autocommit=False, autoflush=False)()
    connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans) -> None:
        if trans.nested and not trans._parent.nested:
            connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
