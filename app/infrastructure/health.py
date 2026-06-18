from dataclasses import dataclass, field

from app.core.database import check_database_connection
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


def run_readiness_checks() -> ReadinessReport:
    checks: list[DependencyCheck] = []

    try:
        check_database_connection()
        checks.append(DependencyCheck(name="database", status="ok"))
    except Exception as exc:
        checks.append(DependencyCheck(name="database", status="error", detail=str(exc)))

    try:
        check_redis_connection()
        checks.append(DependencyCheck(name="redis", status="ok"))
    except Exception as exc:
        checks.append(DependencyCheck(name="redis", status="error", detail=str(exc)))

    overall = "ready" if all(check.status == "ok" for check in checks) else "not_ready"
    return ReadinessReport(status=overall, checks=checks)
