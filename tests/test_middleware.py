import uuid

from app.core.middleware import REQUEST_ID_HEADER


def test_request_id_is_generated_when_missing(client):
    response = client.get("/health")

    request_id = response.headers.get(REQUEST_ID_HEADER)
    assert request_id is not None
    uuid.UUID(request_id)


def test_request_id_is_echoed_when_provided(client):
    expected = str(uuid.uuid4())
    response = client.get("/health", headers={REQUEST_ID_HEADER: expected})

    assert response.headers[REQUEST_ID_HEADER] == expected
