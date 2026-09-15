from collections.abc import Generator
from functools import lru_cache

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_db
from app.infrastructure.accesscore import AccessCoreClient, IntrospectResult


def get_session() -> Generator[Session, None, None]:
    yield from get_db()


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "")


def resolve_actor_id(
    subject: IntrospectResult | None, fallback: str | None = None
) -> str | None:
    """Prefer AccessCore subject; fall back to client-supplied audit string when auth is off."""
    if subject is not None and subject.user_id:
        return subject.user_id
    return fallback


@lru_cache
def _cached_accesscore_client(
    enabled: bool,
    base_url: str,
    api_key: str,
    timeout_seconds: float,
) -> AccessCoreClient:
    return AccessCoreClient(
        base_url=base_url,
        api_key=api_key,
        enabled=enabled,
        timeout_seconds=timeout_seconds,
    )


def get_accesscore_client(
    settings: Settings = Depends(get_settings),
) -> AccessCoreClient:
    return _cached_accesscore_client(
        settings.ACCESSCORE_ENABLED,
        settings.ACCESSCORE_URL,
        settings.ACCESSCORE_API_KEY,
        settings.ACCESSCORE_TIMEOUT_SECONDS,
    )


def extract_bearer_token(request: Request) -> str | None:
    auth = request.headers.get("Authorization") or ""
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        return None
    return token.strip()


def get_current_subject(
    request: Request,
    client: AccessCoreClient = Depends(get_accesscore_client),
    settings: Settings = Depends(get_settings),
) -> IntrospectResult:
    """Resolve AccessCore app session token → subject."""
    if not settings.ACCESSCORE_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "error": {
                    "code": "ACCESSCORE_DISABLED",
                    "message": "AccessCore integration is disabled",
                    "request_id": get_request_id(request),
                }
            },
        )
    raw_token = extract_bearer_token(request)
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "UNAUTHENTICATED",
                    "message": "Bearer token required",
                    "request_id": get_request_id(request),
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    result = client.introspect(raw_token)
    if not result.active or not result.user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": {
                    "code": "SESSION_INVALID",
                    "message": "Session is not valid",
                    "request_id": get_request_id(request),
                }
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    request.state.accesscore_subject = result
    return result


def require_permission(permission: str):
    """FastAPI dependency for ``resource.action``.

    When ``ACCESSCORE_ENABLED`` is false, the check is a no-op so existing
    open APIs keep working until cutover.
    """
    if "." not in permission:
        raise ValueError(f"permission must be 'resource.action', got {permission!r}")
    resource, action = permission.split(".", 1)

    def _enforce(
        request: Request,
        client: AccessCoreClient = Depends(get_accesscore_client),
        settings: Settings = Depends(get_settings),
    ) -> IntrospectResult | None:
        if not settings.ACCESSCORE_ENABLED:
            return None

        raw_token = extract_bearer_token(request)
        if not raw_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "UNAUTHENTICATED",
                        "message": "Bearer token required",
                        "request_id": get_request_id(request),
                    }
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        subject = client.introspect(raw_token)
        if not subject.active or not subject.user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "SESSION_INVALID",
                        "message": "Session is not valid",
                        "request_id": get_request_id(request),
                    }
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        context: dict[str, str] = {"requestId": get_request_id(request)}
        if subject.session_id:
            context["sessionId"] = subject.session_id
        application_id = subject.application_id or settings.ACCESSCORE_APPLICATION_ID
        if application_id:
            context["applicationId"] = application_id
        decision = client.authorize(
            subject=subject.user_id,
            action=action,
            resource=resource,
            context=context,
        )
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "AUTHORIZATION_DENIED",
                        "message": decision.reason or "Not allowed",
                        "request_id": get_request_id(request),
                    }
                },
            )
        request.state.accesscore_subject = subject
        return subject

    return Depends(_enforce)
