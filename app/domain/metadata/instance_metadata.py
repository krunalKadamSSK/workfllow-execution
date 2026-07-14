"""Value Object for business metadata attached to a workflow instance."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class InstanceMetadata(BaseModel):
    """Immutable business metadata for an RFQ-linked workflow revision.

    Follows the Value Object pattern: equality by value, no identity.
    See https://refactoring.guru/design-patterns (domain modeling via VO).
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True, frozen=True)

    rfq_id: str | None = Field(default=None, alias="rfqId")
    estimate_revision: str | None = Field(default=None, alias="estimateRevision")

    @field_validator("rfq_id", "estimate_revision", mode="before")
    @classmethod
    def _blank_to_none(cls, value: Any) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def to_storage(self) -> dict[str, Any]:
        """Serialize using API aliases (rfqId / estimateRevision) plus extras."""
        data = self.model_dump(by_alias=True, exclude_none=False)
        # Drop null core keys so storage stays sparse; keep explicit extras.
        cleaned: dict[str, Any] = {}
        for key, value in data.items():
            if key in {"rfqId", "estimateRevision"} and value is None:
                continue
            cleaned[key] = value
        return cleaned

    @classmethod
    def from_storage(cls, raw: dict[str, Any] | None) -> InstanceMetadata:
        if not raw:
            return cls()
        return cls.model_validate(raw)
