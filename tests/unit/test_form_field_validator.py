import pytest

from app.domain.exceptions import FieldValidationError
from app.domain.validation.fields import FormFieldValidator


def test_required_field_passes():
    validator = FormFieldValidator()
    fields = [{"id": "name", "validation": [{"rule": "required", "message": "required"}]}]
    validator.validate_form(fields, {"name": "ACME"})


def test_required_field_fails():
    validator = FormFieldValidator()
    fields = [{"id": "volume", "validation": [{"rule": "required", "message": "required"}]}]
    with pytest.raises(FieldValidationError) as exc:
        validator.validate_form(fields, {})
    assert exc.value.details[0]["field"] == "volume"


def test_min_rule():
    validator = FormFieldValidator()
    fields = [
        {
            "id": "volume",
            "validation": [{"rule": "min", "value": 1, "message": "min 1"}],
        }
    ]
    with pytest.raises(FieldValidationError):
        validator.validate_form(fields, {"volume": 0})


def test_min_rule_skipped_for_empty_optional_field():
    validator = FormFieldValidator()
    fields = [{"id": "volume", "validation": [{"rule": "min", "value": 1, "message": "min 1"}]}]
    validator.validate_form(fields, {})
