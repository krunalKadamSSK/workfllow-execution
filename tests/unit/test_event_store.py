from app.domain.events.hash_chain import compute_event_hash
from app.domain.events.stored_event import StoredEvent


def test_hash_chain_is_deterministic():
    first = compute_event_hash(
        previous_hash=None,
        sequence_number=1,
        event_type="WORKFLOW_STARTED",
        payload_json={"workflow_instance_id": "inst-1"},
    )
    second = compute_event_hash(
        previous_hash=None,
        sequence_number=1,
        event_type="WORKFLOW_STARTED",
        payload_json={"workflow_instance_id": "inst-1"},
    )
    assert first == second


def test_hash_chain_links_to_previous():
    first_hash = compute_event_hash(
        previous_hash=None,
        sequence_number=1,
        event_type="WORKFLOW_STARTED",
        payload_json={"workflow_instance_id": "inst-1"},
    )
    second_hash = compute_event_hash(
        previous_hash=first_hash,
        sequence_number=2,
        event_type="NODE_COMPLETED",
        payload_json={"workflow_node_id": "node-1"},
    )
    assert first_hash != second_hash


def test_stored_event_from_model():
    class FakeEvent:
        id = "evt-1"
        workflow_instance_id = "inst-1"
        sequence_number = 1
        event_type = "WORKFLOW_STARTED"
        payload_json = {"a": 1}
        previous_hash = None
        current_hash = "abc"
        created_by = None

    stored = StoredEvent.from_model(FakeEvent())
    assert stored.sequence_number == 1
    assert stored.payload_json == {"a": 1}
