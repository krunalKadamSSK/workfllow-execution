"""Readiness checks for dependent infrastructure."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from app.infrastructure.persistence.interfaces.session_manager import SessionManager
from app.infrastructure.persistence.session import get_session_manager
from app.infrastructure.redis_client import check_redis_connection


@dataclass
class DependencyCheck:
    name: str
    status: str
    detail: str | None = None


@dataclass
class ReadinessReport:
    status: str
    checks: list[DependencyCheck] = field(default_factory=list)

    @property
    def is_ready(self) -> bool:
        return self.status == "ready"


@runtime_checkable
class ReadinessChecker(Protocol):
    def run_readiness_checks(self) -> ReadinessReport: ...


class InfrastructureReadinessChecker:
    """Implements ``ReadinessChecker`` for database + Redis."""

    def __init__(self, session_manager: SessionManager | None = None) -> None:
        self._session_manager = session_manager or get_session_manager()

    def run_readiness_checks(self) -> ReadinessReport:
        checks: list[DependencyCheck] = []

        try:
            self._session_manager.check_connection()
            checks.append(DependencyCheck(name="database", status="ok"))
        except Exception as exc:
            checks.append(
                DependencyCheck(name="database", status="error", detail=str(exc))
            )

        try:
            check_redis_connection()
            checks.append(DependencyCheck(name="redis", status="ok"))
        except Exception as exc:
            checks.append(DependencyCheck(name="redis", status="error", detail=str(exc)))

        overall = "ready" if all(check.status == "ok" for check in checks) else "not_ready"
        return ReadinessReport(status=overall, checks=checks)


def run_readiness_checks() -> ReadinessReport:
    """Module-level action used by health routes."""
    return InfrastructureReadinessChecker().run_readiness_checks()
