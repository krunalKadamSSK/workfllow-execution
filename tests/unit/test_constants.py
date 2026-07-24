from app.core.constants import DEFAULT_LIMIT, MAX_LIMIT


def test_pagination_defaults_match_adr_002() -> None:
    assert DEFAULT_LIMIT == 50
    assert MAX_LIMIT == 200
    assert DEFAULT_LIMIT <= MAX_LIMIT
