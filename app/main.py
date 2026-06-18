from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.v1.health import router as health_router
from app.core.config import settings
from app.core.cors import setup_cors
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware, RequestLoggingMiddleware
from app.modules.definitions.router import router as definitions_router
from app.modules.executions.router import router as executions_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RequestContextMiddleware)
setup_cors(app)
register_exception_handlers(app)

app.include_router(health_router)
app.include_router(definitions_router, prefix=settings.API_V1_PREFIX)
app.include_router(executions_router, prefix=settings.API_V1_PREFIX)
