import json
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from app.core.config import settings

_APP_LOGGERS = ("app", "uvicorn", "uvicorn.error", "uvicorn.access")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        request_id = getattr(record, "request_id", None)
        if request_id:
            payload["request_id"] = request_id

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)

        for key, value in record.__dict__.items():
            if key.startswith("_") or key in {
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "exc_info",
                "exc_text",
                "stack_info",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "message",
                "request_id",
            }:
                continue
            payload[key] = value

        return json.dumps(payload, default=str)


def setup_logging() -> None:
    """Configure app log levels without replacing uvicorn's default access logging."""
    level = settings.LOG_LEVEL.upper()

    for name in _APP_LOGGERS:
        logging.getLogger(name).setLevel(level)

    if not settings.LOG_JSON:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())

    for name in _APP_LOGGERS:
        logger = logging.getLogger(name)
        logger.handlers = [handler]
        logger.propagate = False
