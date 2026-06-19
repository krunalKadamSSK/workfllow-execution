import pytest

from app.domain.validation.form_blueprint import validate_form_blueprint


def _minimal_field(**overrides):
    base = {"id": "qty", "type": "number", "label": "Quantity"}
    base.update(overrides)
    return base


def test_valid_blueprint_passes():
    form = {
        "fields": [
            _minimal_field(),
            {
                "id": "total",
                "type": "number",
                "label": "Total",
                "calculation": {"formula": "qty * rate"},
            },
            {"id": "rate", "type": "number", "label": "Rate"},
        ],
        "crossFieldConstraints": [
            {"logic": "qty >= 1", "target": "qty", "message": "Minimum quantity is 1"}
        ],
    }
    assert validate_form_blueprint(form) == []


def test_duplicate_field_id_fails():
    form = {"fields": [_minimal_field(), _minimal_field(id="qty")]}
    issues = validate_form_blueprint(form)
    assert any(issue.code == "DUPLICATE_FIELD_ID" for issue in issues)


def test_unknown_field_type_fails():
    form = {"fields": [_minimal_field(type="datepicker")]}
    issues = validate_form_blueprint(form)
    assert any(issue.code == "UNKNOWN_FIELD_TYPE" for issue in issues)


def test_dangling_formula_reference_fails():
    form = {
        "fields": [
            {
                "id": "total",
                "type": "number",
                "label": "Total",
                "calculation": {"formula": "qty * missing"},
            }
        ]
    }
    issues = validate_form_blueprint(form)
    assert any(issue.code == "DANGLING_FIELD_REFERENCE" for issue in issues)


def test_dangling_remote_requires_fails():
    form = {
        "fields": [
            {
                "id": "customer",
                "type": "select",
                "label": "Customer",
                "remoteOptions": {
                    "url": "/api/customers?country={{countryId}}",
                    "requires": ["countryId"],
                },
            }
        ]
    }
    issues = validate_form_blueprint(form)
    assert any(issue.code == "DANGLING_FIELD_REFERENCE" for issue in issues)


def test_invalid_cross_field_logic_fails():
    form = {
        "fields": [_minimal_field()],
        "crossFieldConstraints": [
            {"logic": "not valid", "target": "qty", "message": "bad logic"}
        ],
    }
    issues = validate_form_blueprint(form)
    assert any(issue.code == "INVALID_CROSS_FIELD_LOGIC" for issue in issues)
