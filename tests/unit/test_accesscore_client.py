"""Unit tests for AccessCore REST client and FastAPI deps."""

from __future__ import annotations

import json

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import (
    _cached_accesscore_client,
    get_accesscore_client,
    require_permission,
    resolve_actor_id,
)
from app.core.config import Settings, get_settings
from app.infrastructure.accesscore import AccessCoreClient, IntrospectResult


def _transport(handler):
    return httpx.MockTransport(handler)


def test_resolve_actor_id_prefers_subject():
    subject = IntrospectResult(active=True, user_id="ac-user-9")
    assert resolve_actor_id(subject, "client-claimed") == "ac-user-9"
    assert resolve_actor_id(None, "client-claimed") == "client-claimed"
    assert resolve_actor_id(IntrospectResult(active=True, user_id=None), "fb") == "fb"


def test_authorize_allow_and_deny():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        if body["action"] == "read":
            return httpx.Response(200, json={"decision": "ALLOW", "reason": ""})
        return httpx.Response(
            200, json={"decision": "DENY", "reason": "missing permission"}
        )

    client = AccessCoreClient(
        base_url="http://accesscore.test",
        api_key="k",
        transport=_transport(handler),
    )
    assert client.authorize(
        subject="u", action="read", resource="workflow_instance"
    ).allowed
    denied = client.authorize(
        subject="u", action="delete", resource="node_definition"
    )
    assert not denied.allowed
    assert denied.reason == "missing permission"


def test_introspect_payload():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-accesscore-key"] == "k"
        assert json.loads(request.content) == {"token": "app-token"}
        return httpx.Response(
            200,
            json={
                "active": True,
                "user_id": "user-1",
                "session_id": "sess-1",
                "application_id": "app-1",
                "expires_in": 60,
            },
        )

    client = AccessCoreClient(
        base_url="http://accesscore.test",
        api_key="k",
        transport=_transport(handler),
    )
    result = client.introspect("app-token")
    assert result.active is True
    assert result.user_id == "user-1"
    assert result.application_id == "app-1"


def test_require_permission_dependency():
    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()

    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.url.path.endswith("/introspect"):
            return httpx.Response(
                200,
                json={
                    "active": True,
                    "user_id": "user-1",
                    "session_id": "sess-1",
                    "expires_in": 30,
                },
            )
        body = json.loads(request.content)
        assert body["resource"] == "workflow_definition"
        assert body["action"] == "read"
        assert body["subject"] == "user-1"
        return httpx.Response(200, json={"decision": "ALLOW", "reason": ""})

    transport = _transport(handler)
    real_client = AccessCoreClient(
        base_url="http://accesscore.test",
        api_key="k",
        enabled=True,
        transport=transport,
    )

    app = FastAPI()

    @app.get(
        "/protected",
        dependencies=[require_permission("workflow_definition.read")],
    )
    def protected():
        return {"ok": True}

    def _settings() -> Settings:
        return Settings(
            ACCESSCORE_ENABLED=True,
            ACCESSCORE_URL="http://accesscore.test",
            ACCESSCORE_API_KEY="k",
        )

    app.dependency_overrides[get_settings] = _settings
    app.dependency_overrides[get_accesscore_client] = lambda: real_client

    client = TestClient(app)
    denied = client.get("/protected")
    assert denied.status_code == 401

    allowed = client.get(
        "/protected", headers={"Authorization": "Bearer app-session-token"}
    )
    assert allowed.status_code == 200
    assert allowed.json() == {"ok": True}
    assert "/v1/sessions/introspect" in calls
    assert "/v1/authorize" in calls

    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()


def test_require_permission_noop_when_disabled():
    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()

    app = FastAPI()

    @app.get(
        "/open",
        dependencies=[require_permission("workflow_instance.read")],
    )
    def open_route():
        return {"ok": True}

    app.dependency_overrides[get_settings] = lambda: Settings(ACCESSCORE_ENABLED=False)
    response = TestClient(app).get("/open")
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()


def test_require_permission_denies():
    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/introspect"):
            return httpx.Response(
                200,
                json={
                    "active": True,
                    "user_id": "user-1",
                    "session_id": "s",
                    "expires_in": 1,
                },
            )
        return httpx.Response(
            200, json={"decision": "DENY", "reason": "missing permission"}
        )

    real_client = AccessCoreClient(
        base_url="http://accesscore.test",
        api_key="k",
        enabled=True,
        transport=_transport(handler),
    )
    app = FastAPI()

    @app.get(
        "/nodes",
        dependencies=[require_permission("node_definition.create")],
    )
    def nodes():
        return {"ok": True}

    app.dependency_overrides[get_settings] = lambda: Settings(
        ACCESSCORE_ENABLED=True,
        ACCESSCORE_URL="http://accesscore.test",
        ACCESSCORE_API_KEY="k",
    )
    app.dependency_overrides[get_accesscore_client] = lambda: real_client

    response = TestClient(app).get(
        "/nodes", headers={"Authorization": "Bearer tok"}
    )
    assert response.status_code == 403
    assert response.json()["detail"]["error"]["code"] == "AUTHORIZATION_DENIED"

    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()


def test_gated_definitions_and_backups_permissions():
    """Definitions + backups routes use the Phase 5 permission names."""
    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()

    authorized: list[tuple[str, str]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/introspect"):
            return httpx.Response(
                200,
                json={
                    "active": True,
                    "user_id": "estimator-1",
                    "session_id": "s",
                    "expires_in": 30,
                },
            )
        body = json.loads(request.content)
        authorized.append((body["resource"], body["action"]))
        allow = (body["resource"], body["action"]) == ("workflow_definition", "read")
        return httpx.Response(
            200,
            json={
                "decision": "ALLOW" if allow else "DENY",
                "reason": "" if allow else "missing permission",
            },
        )

    real_client = AccessCoreClient(
        base_url="http://accesscore.test",
        api_key="k",
        enabled=True,
        transport=_transport(handler),
    )
    app = FastAPI()

    @app.get(
        "/definitions/workflows",
        dependencies=[require_permission("workflow_definition.read")],
    )
    def list_workflows():
        return {"ok": True}

    @app.post(
        "/definitions/nodes",
        dependencies=[require_permission("node_definition.create")],
    )
    def publish_node():
        return {"ok": True}

    @app.get(
        "/backups",
        dependencies=[require_permission("backups.read")],
    )
    def list_backups():
        return {"ok": True}

    app.dependency_overrides[get_settings] = lambda: Settings(
        ACCESSCORE_ENABLED=True,
        ACCESSCORE_URL="http://accesscore.test",
        ACCESSCORE_API_KEY="k",
    )
    app.dependency_overrides[get_accesscore_client] = lambda: real_client

    client = TestClient(app)
    headers = {"Authorization": "Bearer tok"}

    assert client.get("/definitions/workflows", headers=headers).status_code == 200
    assert client.post("/definitions/nodes", headers=headers).status_code == 403
    assert client.get("/backups", headers=headers).status_code == 403
    assert ("workflow_definition", "read") in authorized
    assert ("node_definition", "create") in authorized
    assert ("backups", "read") in authorized

    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()


def test_subject_injected_for_actor_binding():
    """require_permission as a param returns subject for created_by binding."""
    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/introspect"):
            return httpx.Response(
                200,
                json={
                    "active": True,
                    "user_id": "bound-user",
                    "session_id": "s",
                    "expires_in": 30,
                },
            )
        return httpx.Response(200, json={"decision": "ALLOW", "reason": ""})

    real_client = AccessCoreClient(
        base_url="http://accesscore.test",
        api_key="k",
        enabled=True,
        transport=_transport(handler),
    )
    app = FastAPI()

    @app.post("/instances")
    def start(
        subject: IntrospectResult | None = require_permission(
            "workflow_instance.create"
        ),
    ):
        return {"created_by": resolve_actor_id(subject, "spoofed")}

    app.dependency_overrides[get_settings] = lambda: Settings(
        ACCESSCORE_ENABLED=True,
        ACCESSCORE_URL="http://accesscore.test",
        ACCESSCORE_API_KEY="k",
    )
    app.dependency_overrides[get_accesscore_client] = lambda: real_client

    response = TestClient(app).post(
        "/instances", headers={"Authorization": "Bearer tok"}
    )
    assert response.status_code == 200
    assert response.json() == {"created_by": "bound-user"}

    get_settings.cache_clear()
    _cached_accesscore_client.cache_clear()
