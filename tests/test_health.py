from unittest.mock import patch

from fastapi import status

from app.infrastructure.health import DependencyCheck, ReadinessReport


def test_liveness(client):
    response = client.get("/health")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "Workflow Engine"
    assert "environment" in body


def test_readiness_ok_when_dependencies_available(client):
    report = ReadinessReport(
        status="ready",
        checks=[
            DependencyCheck(name="database", status="ok"),
            DependencyCheck(name="redis", status="ok"),
        ],
    )

    with patch("app.api.v1.health.run_readiness_checks", return_value=report):
        response = client.get("/ready")

    assert response.status_code == status.HTTP_200_OK
    body = response.json()
    assert body["status"] == "ready"
    assert len(body["checks"]) == 2


def test_readiness_returns_503_when_dependencies_unavailable(client):
    report = ReadinessReport(
        status="not_ready",
        checks=[
            DependencyCheck(name="database", status="error", detail="connection refused"),
            DependencyCheck(name="redis", status="ok"),
        ],
    )

    with patch("app.api.v1.health.run_readiness_checks", return_value=report):
        response = client.get("/ready")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"][0]["detail"] == "connection refused"
