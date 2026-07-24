"""Application-wide FastAPI dependency factories (class/interface based)."""

from __future__ import annotations

from collections.abc import Generator

from fastapi import Depends, Query, Request
from sqlalchemy.orm import Session

from app.api.controllers.backups import BackupHttpController
from app.api.controllers.definitions.command_controller import DefinitionHttpCommandController
from app.api.controllers.definitions.query_controller import DefinitionHttpQueryController
from app.api.controllers.instances.command_controller import WorkflowInstanceCommandController
from app.api.controllers.instances.query_controller import WorkflowInstanceQueryController
from app.api.controllers.interfaces import (
    BackupController,
    DefinitionCommandController,
    DefinitionQueryController,
    InstanceCommandController,
    InstanceQueryController,
)
from app.api.schemas.common.pagination import PaginationParams
from app.application.executions.service import ExecutionService
from app.core.constants import DEFAULT_LIMIT, MAX_LIMIT
from app.infrastructure.persistence.interfaces.session_manager import SessionManager
from app.infrastructure.persistence.session import get_session_manager


class DatabaseDependencyProvider:
    """Provides DB session dependencies via ``SessionManager``."""

    def __init__(self, session_manager: SessionManager | None = None) -> None:
        self._session_manager = session_manager or get_session_manager()

    def provide_session(self) -> Generator[Session, None, None]:
        yield from self._session_manager.provide_session()

    def resolve_session_manager(self) -> SessionManager:
        return self._session_manager


_db_provider = DatabaseDependencyProvider()


def get_session_manager_dependency() -> SessionManager:
    return _db_provider.resolve_session_manager()


def get_session() -> Generator[Session, None, None]:
    yield from _db_provider.provide_session()


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def get_pagination_params(
    limit: int = Query(DEFAULT_LIMIT, ge=1, le=MAX_LIMIT),
    offset: int = Query(0, ge=0),
) -> PaginationParams:
    return PaginationParams(limit=limit, offset=offset)


def get_execution_service(session: Session = Depends(get_session)) -> ExecutionService:
    return ExecutionService.from_session(session)


def get_instance_command_controller(
    service: ExecutionService = Depends(get_execution_service),
) -> InstanceCommandController:
    return WorkflowInstanceCommandController(service=service)


def get_instance_query_controller(
    service: ExecutionService = Depends(get_execution_service),
) -> InstanceQueryController:
    return WorkflowInstanceQueryController(service=service)


def get_definition_command_controller(
    session: Session = Depends(get_session),
) -> DefinitionCommandController:
    return DefinitionHttpCommandController(session=session)


def get_definition_query_controller(
    session: Session = Depends(get_session),
) -> DefinitionQueryController:
    return DefinitionHttpQueryController(session=session)


def get_backup_controller() -> BackupController:
    return BackupHttpController()
