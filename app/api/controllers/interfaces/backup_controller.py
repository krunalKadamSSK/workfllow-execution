from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from fastapi.responses import JSONResponse

from app.api.schemas.common.pagination import PageResult, PaginationParams


@runtime_checkable
class BackupController(Protocol):
    async def list_backups(
        self, *, pagination: PaginationParams
    ) -> PageResult[dict[str, Any]]: ...

    async def create_backup(self) -> JSONResponse: ...

    async def restore_backup(self, *, backup_id: str) -> JSONResponse: ...

    async def delete_backup(self, *, backup_id: str) -> JSONResponse: ...
