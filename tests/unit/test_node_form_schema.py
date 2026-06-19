from app.domain.validation.form_blueprint import validate_form_blueprint
from app.modules.definitions.schemas.nodes import (
    AppearanceConfig,
    ColorConfig,
    FormConfig,
    IconConfig,
    NodeDefinitionIngest,
)


def _appearance() -> AppearanceConfig:
    return AppearanceConfig(
        icon=IconConfig(kind="lucide", name="FormInput"),
        color=ColorConfig(kind="token", value="primary"),
        shape="card",
        badge="INPUT",
    )


GENERAL_INFORMATION_FORM = {
    "formMeta": {"formId": "general-information", "version": "1.0.0"},
    "fields": [
        {
            "id": "customer_name",
            "type": "select",
            "label": "Customer Name",
            "remoteOptions": {
                "url": "http://localhost:8000/customer_master",
                "labelKey": "name",
                "valueKey": "name",
            },
            "validation": [
                {"rule": "required", "message": "Customer Name is Required"}
            ],
        },
        {
            "id": "cad_part",
            "type": "select",
            "label": "Cad Part",
            "remoteOptions": {
                "url": "http://localhost:8000/cad_part_master",
                "labelKey": "part_name",
                "valueKey": "id",
            },
            "validation": [
                {"rule": "required", "message": "Cad Part name is required"}
            ],
        },
        {
            "id": "casting_process",
            "type": "select",
            "label": "Casting Process",
            "options": [
                {"label": "Gravity Die Casting", "value": "GCD"},
                {"label": "Presure Die Casting", "value": "PCD"},
            ],
            "validation": [
                {"rule": "required", "message": "Casting Process is required.."}
            ],
        },
        {
            "id": "reason_selecting_casting_process",
            "type": "text",
            "label": "Reason For Selecting Casting Process",
            "validation": [
                {
                    "rule": "minLength",
                    "value": 10,
                    "message": "Minimum 10 charecter",
                },
                {
                    "rule": "maxLength",
                    "value": 200,
                    "message": "Maximum length 100",
                },
            ],
        },
        {
            "id": "quantiy",
            "type": "number",
            "label": "Volume",
            "placeholder": "Per Anum",
            "validation": [
                {"rule": "required", "message": "volume is required"},
                {
                    "rule": "min",
                    "value": 1,
                    "message": "Volume Must be greater than 1",
                },
            ],
        },
    ],
}


def test_form_config_preserves_unknown_keys():
    form = FormConfig.model_validate(
        {
            "fields": [],
            "layout": "two-column",
            "schemaVersion": 2,
        }
    )

    dumped = form.model_dump()
    assert dumped["fields"] == []
    assert dumped["layout"] == "two-column"
    assert dumped["schemaVersion"] == 2


def test_form_field_accepts_new_type_and_properties():
    form = FormConfig.model_validate(
        {
            "fields": [
                {
                    "id": "dueDate",
                    "type": "date",
                    "label": "Due date",
                    "helperText": "Optional",
                }
            ]
        }
    )

    field = form.fields[0].model_dump()
    assert field["type"] == "date"
    assert field["helperText"] == "Optional"


def test_general_information_form_from_frontend():
    form = FormConfig.model_validate(GENERAL_INFORMATION_FORM)

    dumped = form.model_dump()
    assert dumped["formMeta"]["formId"] == "general-information"
    assert len(dumped["fields"]) == 5
    assert dumped["fields"][3]["validation"][0]["rule"] == "minLength"
    assert validate_form_blueprint(dumped) == []


def test_to_stored_json_round_trips_evolved_form():
    ingest = NodeDefinitionIngest.model_validate(
        {
            "id": "node-1",
            "name": "Evolved form",
            "slug": "evolved-form",
            "status": "published",
            "version": 1,
            "baseKind": "userInput",
            "appearance": _appearance().model_dump(),
            "form": {
                "fields": [{"id": "name", "type": "text", "label": "Name"}],
                "layout": "grid",
            },
        }
    )

    stored = ingest.to_stored_json()
    assert stored["form"]["layout"] == "grid"
    assert stored["form"]["fields"][0]["id"] == "name"
