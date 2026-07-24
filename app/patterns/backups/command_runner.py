"""Async subprocess runner for backup CLI tools."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.patterns.backups.models import BackupServiceError
from app.patterns.backups.platform import PlatformSupport


class CommandRunner:
    """Executes shell commands with timeout and error handling."""

    def __init__(self, platform_support: PlatformSupport | None = None) -> None:
        self.platform = platform_support or PlatformSupport()

    async def run(
        self,
        cmd: list[str],
        *,
        timeout: int = 600,
        allow_warning_exit: bool = False,
    ) -> None:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **self.platform.subprocess_kwargs(),
        )
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
        except asyncio.TimeoutError as exc:
            process.kill()
            raise BackupServiceError("Backup command timed out", status_code=504) from exc

        return_code = process.returncode or 0
        if allow_warning_exit and return_code == 1:
            return
        if return_code != 0:
            detail = (stderr or stdout or b"").decode("utf-8", errors="replace").strip()
            raise BackupServiceError(
                detail or f"Command failed with exit code {return_code}",
                status_code=500,
            )

    async def run_and_check(self, cmd: list[str], *, error_message: str) -> None:
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            **self.platform.subprocess_kwargs(),
        )
        await process.wait()
        if process.returncode != 0:
            raise BackupServiceError(error_message, status_code=500)

    async def run_to_file(
        self,
        cmd: list[str],
        destination: Path,
        *,
        timeout: int = 600,
    ) -> None:
        """Run a command and stream stdout into a host file (avoids container /tmp)."""
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("wb") as out_file:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=out_file,
                stderr=asyncio.subprocess.PIPE,
                **self.platform.subprocess_kwargs(),
            )
            try:
                _, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except asyncio.TimeoutError as exc:
                process.kill()
                destination.unlink(missing_ok=True)
                raise BackupServiceError("Backup command timed out", status_code=504) from exc

        if (process.returncode or 0) != 0:
            destination.unlink(missing_ok=True)
            detail = (stderr or b"").decode("utf-8", errors="replace").strip()
            raise BackupServiceError(
                detail or f"Command failed with exit code {process.returncode}",
                status_code=500,
            )

    async def run_from_file(
        self,
        cmd: list[str],
        source: Path,
        *,
        timeout: int = 600,
        allow_warning_exit: bool = False,
    ) -> None:
        """Run a command with stdin fed from a host file."""
        with source.open("rb") as in_file:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=in_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                **self.platform.subprocess_kwargs(),
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError as exc:
                process.kill()
                raise BackupServiceError("Backup command timed out", status_code=504) from exc

        return_code = process.returncode or 0
        if allow_warning_exit and return_code == 1:
            return
        if return_code != 0:
            detail = (stderr or stdout or b"").decode("utf-8", errors="replace").strip()
            raise BackupServiceError(
                detail or f"Command failed with exit code {return_code}",
                status_code=500,
            )
