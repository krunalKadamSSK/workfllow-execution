from sqlalchemy import select

from app.domain.exceptions import NotFoundError, ValidationError
from app.infrastructure.db.models.base_types import BaseType
from app.infrastructure.db.repositories.base import BaseRepository


class BaseTypeRepository(BaseRepository):
    def list_base_types(self, *, enabled_only: bool = False) -> list[BaseType]:
        query = select(BaseType).order_by(BaseType.display_name)
        if enabled_only:
            query = query.where(BaseType.enabled.is_(True))
        return list(self.session.scalars(query))

    def get_by_kind(self, kind: str) -> BaseType | None:
        return self.session.scalar(select(BaseType).where(BaseType.kind == kind))

    def require_enabled_kind(self, kind: str) -> BaseType:
        base_type = self.get_by_kind(kind)
        if base_type is None:
            raise NotFoundError(f"Unknown base type: {kind}")
        if not base_type.enabled:
            raise ValidationError(f"Base type is disabled: {kind}")
        return base_type
