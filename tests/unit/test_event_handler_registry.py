from app.application.events.registry import EventHandlerRegistry
from app.domain.events.stored_event import StoredEvent
from app.domain.ports.events import EventHandler


class RecordingHandler:
    def __init__(self, *event_types: str) -> None:
        self._event_types = frozenset(event_types)
        self.received: list[StoredEvent] = []

    def handles(self) -> frozenset[str]:
        return self._event_types

    def handle(self, event: StoredEvent) -> None:
        self.received.append(event)


def test_registry_dispatches_to_matching_handlers():
    registry = EventHandlerRegistry()
    started_handler = RecordingHandler("WORKFLOW_STARTED")
    completed_handler = RecordingHandler("NODE_COMPLETED")
    registry.register(started_handler)
    registry.register(completed_handler)

    event = StoredEvent(
        id="evt-1",
        workflow_instance_id="inst-1",
        sequence_number=1,
        event_type="WORKFLOW_STARTED",
        payload_json={},
    )
    registry.dispatch(event)

    assert len(started_handler.received) == 1
    assert completed_handler.received == []


def test_handler_protocol_compatibility():
    handler = RecordingHandler("NODE_COMPLETED")
    assert isinstance(handler, EventHandler)
