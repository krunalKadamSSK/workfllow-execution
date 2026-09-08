"""Seed data for the base_types catalog."""

BASE_TYPES_SEED: list[dict] = [
    {
        "id": "6a30f2cc1adf6e10e72bcf91",
        "kind": "userInput",
        "display_name": "User task",
        "description": "Form inputs filled at run time",
        "enabled": True,
        "version": "1",
    },
    {
        "id": "6a30f2cc1adf6e10e72bcf94",
        "kind": "table",
        "display_name": "Table task",
        "description": "Dynamic rows with aggregation outputs",
        "enabled": True,
        "version": "1",
    },
    {
        "id": "6a30f2cc1adf6e10e72bcf95",
        "kind": "configTable",
        "display_name": "Config table task",
        "description": "Load configuration DB rows, edit with Synapse fields, aggregations",
        "enabled": True,
        "version": "1",
    },
]
