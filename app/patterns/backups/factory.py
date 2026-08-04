"""Factory Method: creates the backup strategy for the configured deployment mode."""

from __future__ import annotations

from app.core.config import settings
from app.patterns.backups.command_runner import CommandRunner
from app.patterns.backups.models import BackupServiceError, DeploymentMode
from app.patterns.backups.platform import PlatformSupport
from app.patterns.backups.repository import BackupRepository
from app.patterns.backups.strategies import (
    BackupStrategy,
    DockerPostgresBackupStrategy,
    HostPostgresBackupStrategy,
)


class BackupStrategyFactory:
    """Factory Method — selects strategy by deployment mode."""

    @classmethod
    def create(cls, repository: BackupRepository) -> BackupStrategy:
        mode: DeploymentMode = settings.BACKUP_DEPLOYMENT_MODE
        platform = PlatformSupport()
        runner = CommandRunner(platform)
        if mode == "docker":
            return DockerPostgresBackupStrategy(repository, runner=runner, platform=platform)
        if mode in ("local", "remote"):
            return HostPostgresBackupStrategy(repository, runner=runner, platform=platform)
        raise BackupServiceError(
            f"Unsupported backup deployment mode: {mode}",
            status_code=400,
        )
