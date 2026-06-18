from fastapi import APIRouter, Response, status

from app.core.config import settings
from app.infrastructure.health import run_readiness_checks

router = APIRouter(tags=["health"])


@router.get("/health")
def liveness() -> dict:
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@router.get("/ready")
def readiness(response: Response) -> dict:
    report = run_readiness_checks()

    if not report.is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": report.status,
        "service": settings.PROJECT_NAME,
        "checks": [
            {
                "name": check.name,
                "status": check.status,
                **({"detail": check.detail} if check.detail else {}),
            }
            for check in report.checks
        ],
    }
