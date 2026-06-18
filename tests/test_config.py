from app.core.config import normalize_database_url


def test_normalize_asyncpg_url():
    url = "postgresql+asyncpg://user:pass@localhost:5432/db"
    assert normalize_database_url(url) == "postgresql+psycopg://user:pass@localhost:5432/db"


def test_normalize_plain_postgresql_url():
    url = "postgresql://user:pass@localhost:5432/db"
    assert normalize_database_url(url) == "postgresql+psycopg://user:pass@localhost:5432/db"


def test_psycopg_url_unchanged():
    url = "postgresql+psycopg://user:pass@localhost:5432/db"
    assert normalize_database_url(url) == url
