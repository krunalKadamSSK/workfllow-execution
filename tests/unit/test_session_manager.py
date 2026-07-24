from app.infrastructure.persistence.session import (
    SqlAlchemySessionManager,
    get_session_manager,
    reset_session_manager,
)


def test_session_manager_is_singleton() -> None:
    reset_session_manager()
    first = get_session_manager()
    second = get_session_manager()
    assert first is second
    assert isinstance(first, SqlAlchemySessionManager)


def test_session_manager_create_session() -> None:
    manager = get_session_manager()
    session = manager.create_session()
    try:
        assert session is not None
    finally:
        session.close()
