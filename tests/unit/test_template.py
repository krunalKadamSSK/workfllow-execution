import pytest

from app.domain.exceptions import InputResolutionError
from app.domain.executors.template import substitute_templates


def test_substitute_single_variable():
    url = "http://localhost:8000/parts?customer={{customerName}}"
    assert (
        substitute_templates(url, {"customerName": "ACME"})
        == "http://localhost:8000/parts?customer=ACME"
    )


def test_substitute_multiple_variables():
    url = "{{a}}/{{b}}"
    assert substitute_templates(url, {"a": "1", "b": "2"}) == "1/2"


def test_missing_variable_raises():
    with pytest.raises(InputResolutionError):
        substitute_templates("{{missing}}", {})
