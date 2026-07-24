"""Re-export — canonical port lives in ``domain.ports.unit_of_work``."""

from app.domain.ports.unit_of_work import UnitOfWorkPort

__all__ = ["UnitOfWorkPort"]
