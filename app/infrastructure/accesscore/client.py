"""AccessCore peer client — REST only (introspect + authorize)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class AuthorizeDecision:
    allowed: bool
    decision: str
    reason: str


@dataclass(frozen=True)
class IntrospectResult:
    active: bool
    user_id: str | None = None
    session_id: str | None = None
    application_id: str | None = None
    expires_at: str | None = None
    expires_in: int | None = None


class AccessCoreClient:
    """HTTP client for AccessCore ``/v1/sessions/introspect`` and ``/v1/authorize``."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        enabled: bool = True,
        timeout_seconds: float = 5.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.enabled = enabled
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if self.api_key:
            headers["X-AccessCore-Key"] = self.api_key
        return headers

    def authorize(
        self,
        *,
        subject: str,
        action: str,
        resource: str,
        context: dict[str, Any] | None = None,
    ) -> AuthorizeDecision:
        if not self.enabled:
            return AuthorizeDecision(
                allowed=False, decision="DENY", reason="accesscore_disabled"
            )
        payload = {
            "subject": subject,
            "action": action,
            "resource": resource,
            "context": context or {},
        }
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(
                    "/v1/authorize", headers=self._headers(), json=payload
                )
        except httpx.HTTPError as exc:
            logger.warning("AccessCore authorize failed: %s", exc)
            return AuthorizeDecision(
                allowed=False, decision="DENY", reason="accesscore_error"
            )

        if response.status_code == 401:
            return AuthorizeDecision(
                allowed=False, decision="DENY", reason="accesscore_unauthenticated"
            )
        if response.status_code >= 400:
            logger.warning(
                "AccessCore authorize HTTP %s: %s",
                response.status_code,
                response.text[:200],
            )
            return AuthorizeDecision(
                allowed=False, decision="DENY", reason="accesscore_error"
            )

        body = response.json()
        decision = str(body.get("decision") or "DENY").upper()
        reason = str(body.get("reason") or "")
        return AuthorizeDecision(
            allowed=decision == "ALLOW",
            decision=decision,
            reason=reason,
        )

    def introspect(self, raw_token: str) -> IntrospectResult:
        if not self.enabled:
            return IntrospectResult(active=False)
        if not raw_token:
            return IntrospectResult(active=False)
        try:
            with httpx.Client(
                base_url=self.base_url,
                timeout=self.timeout_seconds,
                transport=self._transport,
            ) as client:
                response = client.post(
                    "/v1/sessions/introspect",
                    headers=self._headers(),
                    json={"token": raw_token},
                )
        except httpx.HTTPError as exc:
            logger.warning("AccessCore introspect failed: %s", exc)
            return IntrospectResult(active=False)

        if response.status_code >= 400:
            if response.status_code != 401:
                logger.warning(
                    "AccessCore introspect HTTP %s: %s",
                    response.status_code,
                    response.text[:200],
                )
            return IntrospectResult(active=False)

        body = response.json()
        if not body.get("active"):
            return IntrospectResult(active=False)
        expires_in = body.get("expires_in")
        return IntrospectResult(
            active=True,
            user_id=body.get("user_id"),
            session_id=body.get("session_id"),
            application_id=body.get("application_id"),
            expires_at=body.get("expires_at"),
            expires_in=int(expires_in) if expires_in is not None else None,
        )
