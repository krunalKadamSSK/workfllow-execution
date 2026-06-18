from __future__ import annotations

import dataclasses
from typing import Any


@dataclasses.dataclass(frozen=True)
class StoredEvent:
    id: str
    workflow_instance_id: str
    sequence_number: int
    event_type: str
    payload_json: dict[str, Any]
    previous_hash: str | None = None
    current_hash: str | None = None
    created_by: str | None = None

    @classmethod
    def from_model(cls, event) -> StoredEvent:
        return cls(
            id=event.id,
            workflow_instance_id=event.workflow_instance_id,
            sequence_number=event.sequence_number,
            event_type=event.event_type,
            payload_json=dict(event.payload_json),
            previous_hash=event.previous_hash,
            current_hash=event.current_hash,
            created_by=event.created_by,
        )
