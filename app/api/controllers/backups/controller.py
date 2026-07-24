"""Backup controller — command/query actions over BackupService."""

from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.api.schemas.common.pagination import PageResult, PaginationParams
from app.application.backups import BackupService, BackupServiceError


class BackupHttpController:
    """Implements ``BackupController``."""

    def __init__(self, *, service: BackupService | None = None) -> None:
        self._service = service or BackupService()

    async def list_backups(
        self, *, pagination: PaginationParams
    ) -> PageResult[dict[str, Any]]:
        try:
            page = await self._service.list_backups_page(pagination.to_page_request())
        except BackupServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        return PageResult[dict[str, Any]](
            items=[jsonable_encoder(item.to_dict()) for item in page.items],
            total=page.total,
            limit=page.limit,
            offset=page.offset,
        )

    async def create_backup(self) -> JSONResponse:
        try:
            backup = await self._service.create_backup()
        except BackupServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        return JSONResponse(
            content=jsonable_encoder(
                {
                    "message": "Backup created successfully",
                    "backup": backup.to_dict(),
                }
            ),
            status_code=201,
        )

    async def restore_backup(self, *, backup_id: str) -> JSONResponse:
        try:
            await self._service.restore_backup(backup_id)
        except BackupServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        return JSONResponse(
            content={"message": "Restore completed", "restored_from": backup_id}
        )

    async def delete_backup(self, *, backup_id: str) -> JSONResponse:
        try:
            await self._service.delete_backup(backup_id)
        except BackupServiceError as exc:
            raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
        return JSONResponse(content={"message": "Backup deleted", "deleted": backup_id})
