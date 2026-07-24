"""Facade: simplified backup API over repository and strategy subsystems."""

from __future__ import annotations

from app.application.common.dto.pagination import Page, PageRequest
from app.patterns.backups.factory import BackupStrategyFactory
from app.patterns.backups.models import BackupInfo, BackupServiceError
from app.patterns.backups.repository import BackupRepository
from app.patterns.backups.strategies import BackupStrategy


class BackupService:
    """Facade for list, create, restore, and delete backup operations."""

    def __init__(
        self,
        *,
        repository: BackupRepository | None = None,
        strategy: BackupStrategy | None = None,
    ) -> None:
        self.repository = repository or BackupRepository()
        self.strategy = strategy or BackupStrategyFactory.create(self.repository)

    async def list_backups(self) -> list[BackupInfo]:
        self.repository.require_enabled()
        return self.repository.list_backups()

    async def list_backups_page(self, page: PageRequest) -> Page[BackupInfo]:
        self.repository.require_enabled()
        items, total = self.repository.list_backups_page(
            limit=page.limit, offset=page.offset
        )
        return Page.create_page(
            items=items, total=total, limit=page.limit, offset=page.offset
        )

    async def create_backup(self) -> BackupInfo:
        self.repository.require_enabled()
        backup_id, destination = self.repository.build_destination_path()
        await self.strategy.create_backup(destination)

        if not destination.is_file():
            raise BackupServiceError("Backup file was not created", status_code=500)

        self.repository.apply_retention()
        return self.repository.to_backup_info(backup_id, destination)

    async def restore_backup(self, backup_id: str) -> None:
        self.repository.require_enabled()
        self.repository.require_restore_allowed()
        backup_path = self.repository.resolve_path(backup_id)
        await self.strategy.restore_backup(backup_path)

    async def delete_backup(self, backup_id: str) -> None:
        self.repository.require_enabled()
        self.repository.delete_file(backup_id)
