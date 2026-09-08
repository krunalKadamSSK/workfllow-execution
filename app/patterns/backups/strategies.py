"""Backup execution strategies (Strategy + Template Method patterns)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import settings
from app.patterns.backups.command_runner import CommandRunner
from app.patterns.backups.platform import PlatformSupport
from app.patterns.backups.repository import BackupRepository


class BackupStrategy(ABC):
    """Strategy: defines how backups are created and restored for a deployment mode."""

    def __init__(
        self,
        repository: BackupRepository,
        runner: CommandRunner | None = None,
        platform: PlatformSupport | None = None,
    ) -> None:
        self.repository = repository
        self.platform = platform or PlatformSupport()
        self.runner = runner or CommandRunner(self.platform)

    @property
    def database_name(self) -> str:
        return self.repository.database_name

    def database_url_for_cli(self) -> str:
        url = settings.DATABASE_URL
        return (
            url.replace("postgresql+psycopg://", "postgresql://")
            .replace("postgresql+asyncpg://", "postgresql://")
        )

    async def create_backup(self, destination: Path) -> None:
        """Template Method: orchestrates backup creation."""
        await self._dump_to(destination)

    async def restore_backup(self, source: Path) -> None:
        """Template Method: orchestrates backup restore."""
        await self._restore_from(source)

    @abstractmethod
    async def _dump_to(self, destination: Path) -> None:
        """Hook: engine-specific dump implementation."""

    @abstractmethod
    async def _restore_from(self, source: Path) -> None:
        """Hook: engine-specific restore implementation."""


class DockerPostgresBackupStrategy(BackupStrategy):
    """Strategy: PostgreSQL backup via Docker container.

    Backup streams ``pg_dump`` stdout to the host. Restore copies the dump into
    the container because ``pg_restore`` does not read custom-format archives from stdin.
    """

    REMOTE_PATH = "/tmp/backup.dump"

    @property
    def container(self) -> str:
        return settings.BACKUP_DOCKER_CONTAINER

    async def _dump_to(self, destination: Path) -> None:
        docker = self.platform.docker_command()
        await self.runner.run_to_file(
            [
                docker,
                "exec",
                self.container,
                "pg_dump",
                "-U",
                settings.BACKUP_POSTGRES_USER,
                "-d",
                self.database_name,
                "-Fc",
            ],
            destination,
        )

    async def _restore_from(self, source: Path) -> None:
        docker = self.platform.docker_command()
        await self.runner.run_and_check(
            [
                docker,
                "cp",
                self.platform.host_path(source),
                f"{self.container}:{self.REMOTE_PATH}",
            ],
            error_message="Failed to copy backup into container",
        )
        await self.runner.run(
            [
                docker,
                "exec",
                self.container,
                "pg_restore",
                "-U",
                settings.BACKUP_POSTGRES_USER,
                "-d",
                self.database_name,
                "--clean",
                "--if-exists",
                self.REMOTE_PATH,
            ],
            allow_warning_exit=True,
        )
        await self.runner.run(
            [docker, "exec", self.container, "rm", "-f", self.REMOTE_PATH],
            timeout=30,
        )


class HostPostgresBackupStrategy(BackupStrategy):
    """Strategy: PostgreSQL backup via locally installed pg_dump/pg_restore."""

    async def _dump_to(self, destination: Path) -> None:
        pg_dump = self.platform.resolve_tool("pg_dump")
        await self.runner.run(
            [
                pg_dump,
                "-Fc",
                "-f",
                self.platform.host_path(destination),
                self.database_url_for_cli(),
            ]
        )

    async def _restore_from(self, source: Path) -> None:
        pg_restore = self.platform.resolve_tool("pg_restore")
        await self.runner.run(
            [
                pg_restore,
                "--clean",
                "--if-exists",
                "-d",
                self.database_url_for_cli(),
                self.platform.host_path(source),
            ],
            allow_warning_exit=True,
        )
