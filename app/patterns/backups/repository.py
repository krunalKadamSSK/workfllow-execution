"""Backup file storage (Repository pattern)."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import settings
from app.patterns.backups.models import (
    BACKUP_EXTENSION,
    BACKUP_ID_PATTERN,
    BackupInfo,
    BackupServiceError,
)


class BackupRepository:
    """Manages backup files on disk."""

    def require_enabled(self) -> None:
        if not settings.BACKUP_ENABLED:
            raise BackupServiceError("Backup operations are disabled", status_code=403)

    def require_restore_allowed(self) -> None:
        if not settings.BACKUP_ALLOW_RESTORE:
            raise BackupServiceError("Restore is disabled", status_code=403)

    @property
    def storage_dir(self) -> Path:
        path = Path(settings.BACKUP_STORAGE_DIR)
        if not path.is_absolute():
            path = Path.cwd() / path
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def database_name(self) -> str:
        parsed = urlparse(settings.DATABASE_URL.replace("+psycopg", ""))
        db_path = (parsed.path or "/workflow_engine").lstrip("/")
        return db_path.split("?")[0] or "workflow_engine"

    @property
    def engine(self) -> str:
        return "postgresql"

    def timestamp(self) -> str:
        return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    def build_destination_path(self) -> tuple[str, Path]:
        backup_id = f"workflow_engine_{self.timestamp()}"
        filename = f"{backup_id}{BACKUP_EXTENSION}"
        return backup_id, self.storage_dir / filename

    def resolve_path(self, backup_id: str) -> Path:
        if not BACKUP_ID_PATTERN.match(backup_id):
            raise BackupServiceError("Invalid backup id", status_code=400)

        candidate = self.storage_dir / f"{backup_id}{BACKUP_EXTENSION}"
        if candidate.is_file() and candidate.resolve().is_relative_to(self.storage_dir.resolve()):
            return candidate

        direct = self.storage_dir / backup_id
        if direct.is_file() and direct.resolve().is_relative_to(self.storage_dir.resolve()):
            return direct

        raise BackupServiceError(f"Backup not found: {backup_id}", status_code=404)

    def list_backups(self) -> list[BackupInfo]:
        backups: list[BackupInfo] = []
        for path in sorted(self.storage_dir.iterdir(), reverse=True):
            if not path.is_file() or path.suffix != BACKUP_EXTENSION:
                continue
            stat = path.stat()
            created = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
            backups.append(
                BackupInfo(
                    id=path.stem,
                    filename=path.name,
                    size_bytes=stat.st_size,
                    created_at=created,
                    database=self.database_name,
                    engine=self.engine,
                )
            )
        return backups

    def list_backups_page(self, *, limit: int, offset: int) -> tuple[list[BackupInfo], int]:
        backups = self.list_backups()
        total = len(backups)
        return backups[offset : offset + limit], total

    def to_backup_info(self, backup_id: str, path: Path) -> BackupInfo:
        stat = path.stat()
        return BackupInfo(
            id=backup_id,
            filename=path.name,
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            database=self.database_name,
            engine=self.engine,
        )

    def apply_retention(self) -> None:
        retention = settings.BACKUP_RETENTION_COUNT
        if retention <= 0:
            return
        files = sorted(
            (p for p in self.storage_dir.iterdir() if p.is_file() and p.suffix == BACKUP_EXTENSION),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for stale in files[retention:]:
            stale.unlink(missing_ok=True)

    def delete_file(self, backup_id: str) -> None:
        path = self.resolve_path(backup_id)
        path.unlink(missing_ok=True)
