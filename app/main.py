from fastapi import FastAPI

from app.core.config import settings
from app.core.cors import setup_cors


app = FastAPI(
    title=settings.PROJECT_NAME,
    version="0.1.0"
)

setup_cors(app)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.PROJECT_NAME
    }