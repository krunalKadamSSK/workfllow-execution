import dataclasses
from typing import Any


@dataclasses.dataclass
class ValidationIssue:
    code: str
    message: str
    field: str | None = None
    details: dict[str, Any] = dataclasses.field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.field:
            payload["field"] = self.field
        if self.details:
            payload["details"] = self.details
        return payload
