from unittest.mock import Mock

from app.application.events.handlers.node_projection import WorkflowNodeProjectionHandler
from app.domain.events.stored_event import StoredEvent
from app.domain.events.types import WorkflowEventType


def _stored_event(event_type: str, payload: dict) -> StoredEvent:
    return StoredEvent(
        id="event-1",
        workflow_instance_id="instance-1",
        sequence_number=1,
        event_type=event_type,
        payload_json=payload,
    )


def test_node_projection_handler_clears_values_on_invalidation():
    projections = Mock()
    handler = WorkflowNodeProjectionHandler(projections)

    handler.handle(
        _stored_event(
            WorkflowEventType.NODE_INVALIDATED.value,
            {
                "workflow_node_instance_id": "node-inst-1",
                "workflow_node_id": "node-1",
                "reason": "correction",
            },
        )
    )

    projections.clear_node_projection.assert_called_once_with("node-inst-1")
