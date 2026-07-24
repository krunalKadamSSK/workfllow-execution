"""Aggregate API v1 routers."""

from fastapi import APIRouter

from app.api.routes.v1 import backups, definitions, health, instances

api_v1_router = APIRouter()
api_v1_router.include_router(definitions.router)
api_v1_router.include_router(instances.router)
api_v1_router.include_router(backups.router)

health_router = health.router

__all__ = ["api_v1_router", "health_router"]
