import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

import app.infrastructure.db.models  # noqa: F401
from app.core.config import settings
from app.infrastructure.db.base import Base
from app.infrastructure.db.models.base_types import BaseType
from app.infrastructure.db.seeds.base_types import BASE_TYPES_SEED
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def api_client(db_session) -> TestClient:
    from app.api.deps import get_session

    def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


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
    with Session(engine) as session:
        if session.scalar(text("SELECT COUNT(*) FROM base_types")) == 0:
            session.add_all([BaseType(**row) for row in BASE_TYPES_SEED])
            session.commit()
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
