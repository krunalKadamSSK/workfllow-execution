from sqlalchemy.orm import Session


class BaseRepository:
    """Shared SQLAlchemy repository base (satisfies ``Repository`` Protocol)."""

    def __init__(self, session: Session) -> None:
        self.session = session
