
import os
class Settings:
    PROJECT_NAME: str = "Workflow Engine"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/workflow"
    )

    CORS_ORIGINS = [
        "http://localhost:3000",
        "http://localhost:5173",
    ]


settings = Settings()