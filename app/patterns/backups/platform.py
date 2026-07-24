"""OS detection and platform-specific backup helpers."""

from __future__ import annotations

import platform
import shutil
from pathlib import Path
from typing import Literal

from app.core.config import settings
from app.patterns.backups.models import BackupServiceError

OsFamily = Literal["windows", "linux", "darwin", "other"]
OsOverride = Literal["auto", "windows", "linux", "darwin"]


class PlatformSupport:
    """Resolves OS-specific paths and CLI tools for backup operations."""

    @property
    def os_override(self) -> str:
        return (settings.BACKUP_OS or "auto").strip().lower()

    @property
    def tool_path(self) -> str:
        return (settings.BACKUP_TOOL_PATH or "").strip()

    @property
    def docker_cli_override(self) -> str:
        return (settings.BACKUP_DOCKER_CLI or "").strip()

    @property
    def os_family(self) -> OsFamily:
        if self.os_override in ("windows", "linux", "darwin"):
            return self.os_override
        system = platform.system().lower()
        if system == "windows":
            return "windows"
        if system == "darwin":
            return "darwin"
        if system == "linux":
            return "linux"
        return "other"

    @property
    def is_windows(self) -> bool:
        return self.os_family == "windows"

    def resolve_tool(self, name: str) -> str:
        candidates = [name]
        if self.is_windows and not name.lower().endswith(".exe"):
            candidates.append(f"{name}.exe")

        if self.tool_path:
            for candidate in candidates:
                tool = Path(self.tool_path) / candidate
                if tool.is_file():
                    return str(tool.resolve())

        for candidate in candidates:
            found = shutil.which(candidate)
            if found:
                return found

        hint = (
            "Install PostgreSQL client tools and ensure they are on PATH, "
            "or set BACKUP_TOOL_PATH in .env."
            if self.is_windows
            else "Install pg_dump/pg_restore or set BACKUP_TOOL_PATH in .env."
        )
        raise BackupServiceError(f"{name} not found in PATH. {hint}", status_code=500)

    def docker_command(self) -> str:
        if self.docker_cli_override:
            return self.docker_cli_override
        return self.resolve_tool("docker")

    def host_path(self, path: Path) -> str:
        """Normalize a host path for docker cp (handles Windows drive letters)."""
        resolved = path.resolve()
        if self.is_windows:
            return resolved.as_posix()
        return str(resolved)

    def subprocess_kwargs(self) -> dict:
        if not self.is_windows:
            return {}
        return {"creationflags": 0x08000000}  # CREATE_NO_WINDOW
