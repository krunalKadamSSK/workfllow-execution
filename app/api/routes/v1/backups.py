"""Backup routes under /api/v1/backups."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.controllers.interfaces import BackupController
from app.api.deps import get_backup_controller, get_pagination_params
from app.api.schemas.common.pagination import PageResult, PaginationParams

router = APIRouter(prefix="/backups", tags=["Backups"])


@router.get("", response_model=PageResult[dict[str, Any]])
async def list_backups(
    pagination: PaginationParams = Depends(get_pagination_params),
    controller: BackupController = Depends(get_backup_controller),
) -> PageResult[dict[str, Any]]:
    return await controller.list_backups(pagination=pagination)


@router.post("", response_class=JSONResponse)
async def create_backup(
    controller: BackupController = Depends(get_backup_controller),
) -> JSONResponse:
    return await controller.create_backup()


@router.post("/{backup_id}/restore", response_class=JSONResponse)
async def restore_backup(
    backup_id: str,
    controller: BackupController = Depends(get_backup_controller),
) -> JSONResponse:
    return await controller.restore_backup(backup_id=backup_id)


@router.delete("/{backup_id}", response_class=JSONResponse)
async def delete_backup(
    backup_id: str,
    controller: BackupController = Depends(get_backup_controller),
) -> JSONResponse:
    return await controller.delete_backup(backup_id=backup_id)
