from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.domain.exceptions import NotFoundError, SequenceConflictError
from app.infrastructure.db.models import WorkflowEvent
from app.infrastructure.db.repositories.base import BaseRepository


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
        self.session.add(event)
        try:
            self.session.flush()
        except IntegrityError as exc:
            raise SequenceConflictError(
                f"Event sequence conflict for workflow instance {workflow_instance_id} "
                f"at sequence {sequence}"
            ) from exc
        return event

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
        query = select(WorkflowEvent).where(
            WorkflowEvent.workflow_instance_id == workflow_instance_id
        )
        if after_sequence is not None:
            query = query.where(WorkflowEvent.sequence_number > after_sequence)
        query = query.order_by(WorkflowEvent.sequence_number.asc())
        return list(self.session.scalars(query))

    def list_all_events(self) -> list[WorkflowEvent]:
        return list(
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
