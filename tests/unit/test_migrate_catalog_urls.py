from app.domain.definitions.migrate_catalog_urls import (
    migrate_node_definition_json,
    migrate_synapse_url_template,
)


def test_migrate_synapse_url_template_strips_host() -> None:
    assert (
        migrate_synapse_url_template("http://localhost:8000/customer_master")
        == "/customer_master"
    )
    assert (
        migrate_synapse_url_template(
            "https://config.example.com/cost_item_master?categoryId={{categoryId}}"
        )
        == "/cost_item_master?categoryId={{categoryId}}"
    )


def test_migrate_synapse_url_template_keeps_relative() -> None:
    assert (
        migrate_synapse_url_template("/customer_master?id={{x}}")
        == "/customer_master?id={{x}}"
    )


def test_migrate_node_definition_json_user_input() -> None:
    original = {
        "baseKind": "userInput",
        "form": {
            "fields": [
                {
                    "id": "customer",
                    "type": "select",
                    "label": "Customer",
                    "remoteOptions": {
                        "url": "http://localhost:8000/customer_master",
                        "labelKey": "name",
                        "valueKey": "id",
                    },
                }
            ]
        },
    }
    migrated = migrate_node_definition_json(original)
    assert migrated is not None
    assert (
        migrated["form"]["fields"][0]["remoteOptions"]["url"] == "/customer_master"
    )
    # Original not mutated
    assert (
        original["form"]["fields"][0]["remoteOptions"]["url"]
        == "http://localhost:8000/customer_master"
    )


def test_migrate_node_definition_json_table_and_config_table() -> None:
    original = {
        "baseKind": "table",
        "table": {
            "headerFields": [
                {
                    "id": "h",
                    "remoteOptions": {"url": "http://old/items"},
                }
            ],
            "columns": [
                {
                    "id": "c",
                    "remoteSource": {
                        "url": "http://old/rates?x={{h}}",
                        "resultPath": "0.v",
                    },
                }
            ],
        },
        "configTable": {
            "queryInputs": [
                {
                    "id": "q",
                    "remoteOptions": {"url": "http://localhost:8000/regions"},
                }
            ],
            "columnMappings": [
                {
                    "dbField": "name",
                    "field": {
                        "id": "name",
                        "remoteSource": {
                            "url": "http://localhost:8000/extra?id={{q}}",
                            "resultPath": "0.v",
                        },
                    },
                }
            ],
            "extraColumns": [],
        },
    }
    migrated = migrate_node_definition_json(original)
    assert migrated is not None
    assert migrated["table"]["headerFields"][0]["remoteOptions"]["url"] == "/items"
    assert migrated["table"]["columns"][0]["remoteSource"]["url"] == "/rates?x={{h}}"
    assert (
        migrated["configTable"]["queryInputs"][0]["remoteOptions"]["url"] == "/regions"
    )
    assert (
        migrated["configTable"]["columnMappings"][0]["field"]["remoteSource"]["url"]
        == "/extra?id={{q}}"
    )


def test_migrate_node_definition_json_noop_when_already_relative() -> None:
    original = {
        "baseKind": "userInput",
        "form": {
            "fields": [
                {
                    "id": "a",
                    "remoteOptions": {"url": "/customer_master"},
                }
            ]
        },
    }
    assert migrate_node_definition_json(original) is None
