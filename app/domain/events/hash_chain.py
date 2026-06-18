from __future__ import annotations

import hashlib
import json
from typing import Any


def compute_event_hash(
    *,
    previous_hash: str | None,
    sequence_number: int,
    event_type: str,
    payload_json: dict[str, Any],
) -> str:
    canonical = json.dumps(
        {
            "previous_hash": previous_hash,
            "sequence_number": sequence_number,
            "event_type": event_type,
            "payload_json": payload_json,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
