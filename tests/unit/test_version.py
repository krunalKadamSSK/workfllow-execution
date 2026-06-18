import pytest

from app.application.definitions.version import parse_version


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1", 1),
        ("1.0.0", 1),
        (2, 2),
    ],
)
def test_parse_version(raw, expected):
    assert parse_version(raw) == expected


def test_parse_version_rejects_empty():
    with pytest.raises(ValueError):
        parse_version("")
