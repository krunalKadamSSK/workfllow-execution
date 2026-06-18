from collections.abc import Callable
from contextlib import AbstractContextManager

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.infrastructure.db.repositories.definitions import DefinitionRepository
from app.infrastructure.db.repositories.events import EventRepository
from app.infrastructure.db.repositories.instances import InstanceRepository


class UnitOfWork(AbstractContextManager):
    def __init__(self, session_factory: Callable[[], Session] | None = None) -> None:
        self._session_factory = session_factory or SessionLocal
        self._owns_session = session_factory is None
        self.session: Session | None = None
        self.definitions: DefinitionRepository | None = None
        self.instances: InstanceRepository | None = None
        self.events: EventRepository | None = None

    def __enter__(self) -> "UnitOfWork":
        self.session = self._session_factory()
        self.definitions = DefinitionRepository(self.session)
        self.instances = InstanceRepository(self.session)
        self.events = EventRepository(self.session)
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

    def commit(self) -> None:
        assert self.session is not None
        self.session.commit()

    def rollback(self) -> None:
        assert self.session is not None
        self.session.rollback()
