from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.application.common.dto.pagination import Page, PageRequest
from app.domain.exceptions import NotFoundError, SequenceConflictError
from app.infrastructure.persistence.models.events import WorkflowEvent
from app.infrastructure.persistence.paginator import SqlAlchemyQueryPaginator
from app.infrastructure.persistence.repositories.base import BaseRepository

_SEQUENCE_APPEND_MAX_RETRIES = 3


class EventRepository(BaseRepository):
    def get_next_sequence_number(self, workflow_instance_id: str) -> int:
        current = self.session.scalar(
            select(func.coalesce(func.max(WorkflowEvent.sequence_number), 0)).where(
                WorkflowEvent.workflow_instance_id == workflow_instance_id
            )
        )
        return int(current or 0) + 1

    def append_event(
        self,
        *,
        workflow_instance_id: str,
        event_type: str,
        payload_json: dict,
        created_by: str | None = None,
        previous_hash: str | None = None,
        current_hash: str | None = None,
        sequence_number: int | None = None,
    ) -> WorkflowEvent:
        last_error: IntegrityError | None = None

        for _ in range(_SEQUENCE_APPEND_MAX_RETRIES):
            sequence = (
                sequence_number
                if sequence_number is not None
                else self.get_next_sequence_number(workflow_instance_id)
            )
            event = WorkflowEvent(
                workflow_instance_id=workflow_instance_id,
                sequence_number=sequence,
                event_type=event_type,
                payload_json=payload_json,
                created_by=created_by,
                previous_hash=previous_hash,
                current_hash=current_hash,
            )
            try:
                with self.session.begin_nested():
                    self.session.add(event)
                    self.session.flush()
                return event
            except IntegrityError as exc:
                last_error = exc
                sequence_number = None

        raise SequenceConflictError(
            f"Event sequence conflict for workflow instance {workflow_instance_id}"
        ) from last_error

    def get_latest_event(self, workflow_instance_id: str) -> WorkflowEvent | None:
        return self.session.scalar(
            select(WorkflowEvent)
            .where(WorkflowEvent.workflow_instance_id == workflow_instance_id)
            .order_by(WorkflowEvent.sequence_number.desc())
            .limit(1)
        )

    def list_events(
        self, workflow_instance_id: str, *, after_sequence: int | None = None
    ) -> list[WorkflowEvent]:
        query = self._build_events_statement(
            workflow_instance_id, after_sequence=after_sequence
        )
        return list[WorkflowEvent](self.session.scalars(query))

    def list_events_page(
        self,
        workflow_instance_id: str,
        page: PageRequest,
        *,
        after_sequence: int | None = None,
        event_type: str | None = None,
    ) -> Page[WorkflowEvent]:
        statement = self._build_events_statement(
            workflow_instance_id,
            after_sequence=after_sequence,
            event_type=event_type,
        )
        return SqlAlchemyQueryPaginator().fetch_page(self.session, statement, page)

    def _build_events_statement(
        self,
        workflow_instance_id: str,
        *,
        after_sequence: int | None = None,
        event_type: str | None = None,
    ):
        query = select(WorkflowEvent).where(
            WorkflowEvent.workflow_instance_id == workflow_instance_id
        )
        if after_sequence is not None:
            query = query.where(WorkflowEvent.sequence_number > after_sequence)
        if event_type is not None:
            query = query.where(WorkflowEvent.event_type == event_type)
        return query.order_by(WorkflowEvent.sequence_number.asc())

    def list_all_events(self) -> list[WorkflowEvent]:
        return list[WorkflowEvent](
            self.session.scalars(
                select(WorkflowEvent).order_by(
                    WorkflowEvent.workflow_instance_id,
                    WorkflowEvent.sequence_number,
                )
            )
        )

    def get_event(self, event_id: str) -> WorkflowEvent | None:
        return self.session.get(WorkflowEvent, event_id)

    def require_event(self, event_id: str) -> WorkflowEvent:
        event = self.get_event(event_id)
        if event is None:
            raise NotFoundError(f"Workflow event not found: {event_id}")
        return event
