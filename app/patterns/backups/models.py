"""Backup domain models and errors."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any, Literal

DeploymentMode = Literal["docker", "local", "remote"]
BACKUP_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]+$")
BACKUP_EXTENSION = ".dump"


@dataclass(frozen=True)
class BackupInfo:
    id: str
    filename: str
    size_bytes: int
    created_at: str
    database: str
    engine: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class BackupServiceError(Exception):
    """Raised when backup operations fail."""

    def __init__(self, message: str, *, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
