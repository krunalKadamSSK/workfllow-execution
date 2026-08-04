"""Strategy helpers: decide which form fields may be seeded from a prior revision."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class FieldSeedClassifier(Protocol):
    """Strategy: classify whether a field value should be copied on re-estimate."""

    def is_static(self, field: dict[str, Any]) -> bool:
        """Return True when the field is user-entered (not calculation / API)."""
        ...


class StaticFieldClassifier:
    """Seed only static inputs; recalculate formulas and remote/API field values.

    Strategy pattern — https://refactoring.guru/design-patterns/strategy

    Notes:
    - ``calculation`` → derived; do not seed
    - ``remoteSource`` → field value fetched from API; do not seed
    - ``remoteOptions`` → only option list is remote; selected value is static → seed
    """

    def is_static(self, field: dict[str, Any]) -> bool:
        if not isinstance(field, dict):
            return False
        if field.get("calculation"):
            return False
        if field.get("remoteSource"):
            return False
        return True


def filter_static_outputs(
    *,
    outputs: dict[str, Any],
    fields: list[dict[str, Any]],
    classifier: FieldSeedClassifier | None = None,
) -> dict[str, Any]:
    """Keep output keys that map to static fields only."""
    active = classifier or StaticFieldClassifier()
    static_ids = {
        str(field["id"])
        for field in fields
        if isinstance(field, dict) and "id" in field and active.is_static(field)
    }
    return {
        key: value
        for key, value in outputs.items()
        if str(key) in static_ids and not str(key).startswith("__")
    }
