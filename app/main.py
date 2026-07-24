from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routes.v1.router import api_v1_router, health_router
from app.api.routes.v2.router import api_v2_router
from app.core.config import settings
from app.core.cors import setup_cors
from app.core.logging import setup_logging
from app.core.middleware import RequestContextMiddleware


@asynccontextmanager
async def lifespan(_: FastAPI):
    setup_logging()
    yield


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(RequestContextMiddleware)
setup_cors(app)
register_exception_handlers(app)

app.include_router(health_router)
app.include_router(api_v1_router, prefix=settings.API_V1_PREFIX)
app.include_router(api_v2_router)  # reserved; empty until breaking v2 contracts
