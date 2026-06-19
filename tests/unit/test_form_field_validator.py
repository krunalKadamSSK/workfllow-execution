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


def test_min_length_rule():
    validator = FormFieldValidator()
    fields = [
        {
            "id": "reason",
            "validation": [{"rule": "minLength", "value": 10, "message": "too short"}],
        }
    ]
    with pytest.raises(FieldValidationError) as exc:
        validator.validate_form(fields, {"reason": "short"})
    assert exc.value.details[0]["rule"] == "minLength"


def test_max_length_rule():
    validator = FormFieldValidator()
    fields = [
        {
            "id": "reason",
            "validation": [{"rule": "maxLength", "value": 5, "message": "too long"}],
        }
    ]
    with pytest.raises(FieldValidationError):
        validator.validate_form(fields, {"reason": "way too long"})


def test_regex_rule():
    validator = FormFieldValidator()
    fields = [
        {
            "id": "code",
            "validation": [{"rule": "regex", "value": r"[A-Z]{3}", "message": "bad code"}],
        }
    ]
    with pytest.raises(FieldValidationError):
        validator.validate_form(fields, {"code": "abc"})


def test_pattern_alias():
    validator = FormFieldValidator()
    fields = [
        {
            "id": "code",
            "validation": [{"rule": "pattern", "value": r"[A-Z]{3}", "message": "bad code"}],
        }
    ]
    validator.validate_form(fields, {"code": "ABC"})


def test_email_rule():
    validator = FormFieldValidator()
    fields = [{"id": "email", "validation": [{"rule": "email", "message": "invalid email"}]}]
    with pytest.raises(FieldValidationError):
        validator.validate_form(fields, {"email": "not-an-email"})


def test_url_rule():
    validator = FormFieldValidator()
    fields = [{"id": "site", "validation": [{"rule": "url", "message": "invalid url"}]}]
    with pytest.raises(FieldValidationError):
        validator.validate_form(fields, {"site": "not-a-url"})


def test_uuid_rule():
    validator = FormFieldValidator()
    fields = [{"id": "id", "validation": [{"rule": "uuid", "message": "invalid uuid"}]}]
    validator.validate_form(
        fields, {"id": "550e8400-e29b-41d4-a716-446655440000"}
    )


def test_cross_field_constraint_passes():
    validator = FormFieldValidator()
    validator.validate_form(
        [{"id": "qty", "validation": []}],
        {"qty": 5},
        cross_field_constraints=[
            {"logic": "qty >= 1", "target": "qty", "message": "qty must be at least 1"}
        ],
    )


def test_cross_field_constraint_fails():
    validator = FormFieldValidator()
    with pytest.raises(FieldValidationError) as exc:
        validator.validate_form(
            [{"id": "discountPct", "validation": []}],
            {"discountPct": 150},
            cross_field_constraints=[
                {
                    "logic": "discountPct <= 100",
                    "target": "discountPct",
                    "message": "Discount cannot exceed 100",
                }
            ],
        )
    assert exc.value.details[0]["rule"] == "crossField"
