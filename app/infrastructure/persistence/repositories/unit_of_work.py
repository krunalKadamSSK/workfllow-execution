from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
from typing import cast

from sqlalchemy.orm import Session

from app.application.events.event_store import EventStore
from app.application.events.factory import create_default_event_handler_registry
from app.application.events.rebuilder import ProjectionRebuilder
from app.core.config import settings
from app.domain.ports.event_repository import EventRepositoryPort
from app.domain.ports.instance_repository import InstanceRepositoryPort
from app.domain.ports.projection_repository import ProjectionRepositoryPort
from app.infrastructure.persistence.interfaces.session_manager import SessionManager
from app.infrastructure.persistence.repositories.definitions import DefinitionRepository
from app.infrastructure.persistence.repositories.events import EventRepository
from app.infrastructure.persistence.repositories.instances import InstanceRepository
from app.infrastructure.persistence.repositories.projections import ProjectionRepository
from app.infrastructure.persistence.session import get_session_manager


class UnitOfWork(AbstractContextManager["UnitOfWork"]):
    """Implements ``UnitOfWorkPort`` — owns commit/rollback for a unit of work."""

    def __init__(
        self,
        *,
        session_factory: Callable[[], Session] | None = None,
        session_manager: SessionManager | None = None,
    ) -> None:
        if session_factory is not None:
            self._session_factory = session_factory
            self._owns_session = True
        else:
            manager = session_manager or get_session_manager()
            self._session_factory = manager.create_session
            self._owns_session = True
        self.session: Session | None = None
        self.definitions: DefinitionRepository | None = None
        self.instances: InstanceRepository | None = None
        self.events: EventRepository | None = None
        self.projections: ProjectionRepository | None = None
        self.event_store: EventStore | None = None
        self.projection_rebuilder: ProjectionRebuilder | None = None

    def __enter__(self) -> UnitOfWork:
        self.session = self._session_factory()
        self.definitions = DefinitionRepository(self.session)
        self.instances = InstanceRepository(self.session)
        self.events = EventRepository(self.session)
        self.projections = ProjectionRepository(self.session)

        # Concrete repos satisfy the ports structurally; cast for the type checker
        # (page DTOs live in application, so port signatures stay intentionally loose).
        instances_port = cast(InstanceRepositoryPort, self.instances)
        projections_port = cast(ProjectionRepositoryPort, self.projections)
        events_port = cast(EventRepositoryPort, self.events)

        handler_registry = create_default_event_handler_registry(
            projection_repository=projections_port,
            instance_repository=instances_port,
        )
        self.event_store = EventStore(
            events_port,
            handler_registry,
            hash_chain_enabled=settings.EVENT_HASH_CHAIN,
        )
        self.projection_rebuilder = ProjectionRebuilder(
            event_repository=events_port,
            projection_repository=projections_port,
            handler_registry=handler_registry,
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        assert self.session is not None
        if self._owns_session:
            if exc_type is not None:
                self.session.rollback()
            else:
                self.session.commit()
            self.session.close()
        self.session = None
        self.definitions = None
        self.instances = None
        self.events = None
        self.projections = None
        self.event_store = None
        self.projection_rebuilder = None

    def commit(self) -> None:
        assert self.session is not None
        self.session.commit()

    def rollback(self) -> None:
        assert self.session is not None
        self.session.rollback()
