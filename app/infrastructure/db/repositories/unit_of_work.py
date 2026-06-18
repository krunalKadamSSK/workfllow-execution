from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from app.application.events.event_store import EventStore
from app.application.events.factory import create_default_event_handler_registry
from app.application.events.rebuilder import ProjectionRebuilder
from app.core.config import settings
from app.core.database import SessionLocal
from app.infrastructure.db.repositories.definitions import DefinitionRepository
from app.infrastructure.db.repositories.events import EventRepository
from app.infrastructure.db.repositories.instances import InstanceRepository
from app.infrastructure.db.repositories.projections import ProjectionRepository


class UnitOfWork(AbstractContextManager):
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal
        self._owns_session = session_factory is None
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

        handler_registry = create_default_event_handler_registry(
            projection_repository=self.projections,
            instance_repository=self.instances,
        )
        self.event_store = EventStore(
            self.events,
            handler_registry,
            hash_chain_enabled=settings.EVENT_HASH_CHAIN,
        )
        self.projection_rebuilder = ProjectionRebuilder(
            event_repository=self.events,
            projection_repository=self.projections,
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
