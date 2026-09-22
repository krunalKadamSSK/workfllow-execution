from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(url: str) -> str:
    """Ensure sync SQLAlchemy uses the psycopg driver."""
    if url.startswith("postgresql+asyncpg://"):
        return url.replace("postgresql+asyncpg://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    PROJECT_NAME: str = "Workflow Engine"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = Field(
        default="postgresql+psycopg://workflow:workflow@localhost:5432/workflow_engine"
    )
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    CORS_ORIGINS: list[str] = Field(
        default=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
        ]
    )

    LOG_LEVEL: str = "INFO"
    LOG_JSON: bool = False
    EVENT_HASH_CHAIN: bool = False

    # AccessCore REST peer auth. When true, route guards enforce Bearer + authorize.
    # Keep false in automated tests without AccessCore; enable for local/prod cutover.
    ACCESSCORE_ENABLED: bool = False
    ACCESSCORE_URL: str = "http://localhost:8081"
    ACCESSCORE_API_KEY: str = ""
    ACCESSCORE_APPLICATION_ID: str = ""
    ACCESSCORE_TIMEOUT_SECONDS: float = 5.0

    BACKUP_ENABLED: bool = True
    BACKUP_STORAGE_DIR: str = "backups"
    BACKUP_DEPLOYMENT_MODE: Literal["docker", "local", "remote"] = "docker"
    BACKUP_OS: Literal["auto", "windows", "linux", "darwin"] = "auto"
    BACKUP_DOCKER_CONTAINER: str = "workflow_engine_postgres"
    BACKUP_DOCKER_CLI: str = ""
    BACKUP_POSTGRES_USER: str = "workflow"
    BACKUP_TOOL_PATH: str = ""
    BACKUP_RETENTION_COUNT: int = 20
    BACKUP_ALLOW_RESTORE: bool = True
    # Phase 5: HTTP /backups routes off by default (use Backup Ops). CLI make db-backup unchanged.
    LEGACY_HTTP_BACKUPS_ENABLED: bool = False

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def _normalize_database_url(cls, value: str) -> str:
        return normalize_database_url(value)

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
