"""Unit tests for RFQ instance metadata VO and static seed Strategy."""

from app.domain.metadata import InstanceMetadata
from app.domain.seed import StaticFieldClassifier, filter_static_outputs


def test_instance_metadata_round_trip_aliases():
    meta = InstanceMetadata.model_validate(
        {"rfqId": "RFQ-2026-0001", "estimateRevision": "1", "note": "first"}
    )
    assert meta.rfq_id == "RFQ-2026-0001"
    assert meta.estimate_revision == "1"
    storage = meta.to_storage()
    assert storage["rfqId"] == "RFQ-2026-0001"
    assert storage["estimateRevision"] == "1"
    assert storage["note"] == "first"
    restored = InstanceMetadata.from_storage(storage)
    assert restored.rfq_id == "RFQ-2026-0001"
    assert restored.estimate_revision == "1"


def test_instance_metadata_blank_strings_become_none():
    meta = InstanceMetadata.model_validate({"rfqId": "  ", "estimateRevision": ""})
    assert meta.rfq_id is None
    assert meta.estimate_revision is None
    assert meta.to_storage() == {}


def test_static_field_classifier_skips_calculation_and_remote():
    classifier = StaticFieldClassifier()
    assert classifier.is_static({"id": "customerName", "type": "text"}) is True
    assert (
        classifier.is_static(
            {
                "id": "customerName",
                "type": "select",
                "remoteOptions": {"url": "http://localhost:8000/customer_master"},
            }
        )
        is True
    )
    assert (
        classifier.is_static(
            {"id": "inputWeight", "type": "number", "calculation": {"formula": "a+b"}}
        )
        is False
    )
    assert (
        classifier.is_static(
            {"id": "rate", "type": "number", "remoteSource": {"url": "/api/rate"}}
        )
        is False
    )


def test_filter_static_outputs_keeps_only_static_keys():
    fields = [
        {"id": "customerName", "type": "text"},
        {"id": "meltLossPercentage", "type": "number"},
        {"id": "inputWeight", "type": "number", "calculation": {"formula": "a+b"}},
        {"id": "rate", "type": "number", "remoteSource": {"url": "/x"}},
    ]
    outputs = {
        "customerName": "ACME",
        "meltLossPercentage": 5,
        "inputWeight": 15,
        "rate": 99,
        "__internal": True,
    }
    seeded = filter_static_outputs(outputs=outputs, fields=fields)
    assert seeded == {"customerName": "ACME", "meltLossPercentage": 5}
