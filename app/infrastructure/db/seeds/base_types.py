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
        "id": "6a30f2cc1adf6e10e72bcf92",
        "kind": "ai",
        "display_name": "AI task",
        "description": "LLM step with model and API credentials",
        "enabled": True,
        "version": "1",
    },
    {
        "id": "6a30f2cc1adf6e10e72bcf93",
        "kind": "script",
        "display_name": "Script task",
        "description": "JavaScript logic with live testing in the designer",
        "enabled": True,
        "version": "1",
    },
]
