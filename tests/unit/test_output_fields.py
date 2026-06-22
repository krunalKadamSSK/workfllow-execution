from app.domain.definitions.output_fields import (
    collect_output_field_ids,
    cost_contribution,
    declared_output,
    validate_declared_output,
)


def test_declared_output_returns_key_and_label():
    definition = {
        "output": {"id": "inputWeight", "label": "Line total"},
        "form": {"fields": [{"id": "inputWeight", "type": "number", "label": "input weight"}]},
    }
    assert declared_output(definition) == {"id": "inputWeight", "label": "Line total"}


def test_declared_output_missing_returns_none():
    assert declared_output({"form": {"fields": []}}) is None


def test_collect_output_field_ids_includes_form_and_declared_output():
    definition = {
        "output": {"id": "inputWeight", "label": "Line total"},
        "form": {
            "fields": [
                {"id": "customerName", "type": "text", "label": "customer"},
                {"id": "inputWeight", "type": "number", "label": "input weight"},
            ]
        },
    }
    assert collect_output_field_ids(definition) == {"customerName", "inputWeight"}


def test_cost_contribution_extracts_integer_declared_output():
    definition = {"output": {"id": "inputWeight", "label": "Line total"}}
    assert cost_contribution(definition, {"inputWeight": 15}) == 15.0


def test_cost_contribution_extracts_float_declared_output():
    definition = {"output": {"id": "inputWeight", "label": "Line total"}}
    assert cost_contribution(definition, {"inputWeight": 15.5}) == 15.5


def test_cost_contribution_ignores_non_numeric_values():
    definition = {"output": {"id": "inputWeight", "label": "Line total"}}
    assert cost_contribution(definition, {"inputWeight": "15"}) is None
    assert cost_contribution(definition, {}) is None


def test_cost_contribution_without_declared_output_returns_none():
    assert cost_contribution({"form": {"fields": []}}, {"volume": 10}) is None


def test_validate_declared_output_passes_for_number_field_without_integer_rule():
    definition = {
        "output": {"id": "inputWeight", "label": "Line total"},
        "form": {
            "fields": [
                {
                    "id": "inputWeight",
                    "type": "number",
                    "label": "input weight",
                    "validation": [{"rule": "required", "message": "required"}],
                }
            ]
        },
    }
    assert validate_declared_output(definition) == []


def test_validate_declared_output_rejects_non_number_field():
    definition = {
        "output": {"id": "customerName", "label": "Line total"},
        "form": {
            "fields": [
                {"id": "customerName", "type": "text", "label": "customer"},
            ]
        },
    }
    issues = validate_declared_output(definition)
    assert any(issue.code == "INVALID_OUTPUT_FIELD_TYPE" for issue in issues)
