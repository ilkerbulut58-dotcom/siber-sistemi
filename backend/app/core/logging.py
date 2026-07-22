"""Structured logging configuration."""

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

from pythonjsonlogger.json import JsonFormatter

from app.core.config import get_settings

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="")


class RequestIdFilter(logging.Filter):
    """Inject request_id from context into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = request_id_ctx.get() or "-"
        return True


class SensitiveDataFilter(logging.Filter):
    """Mask common sensitive patterns in log messages."""

    SENSITIVE_KEYS = ("password", "token", "secret", "authorization", "api_key")

    def filter(self, record: logging.LogRecord) -> bool:
        msg = str(record.getMessage()).lower()
        for key in self.SENSITIVE_KEYS:
            if key in msg:
                record.msg = "[REDACTED - sensitive data]"
                record.args = ()
                break
        return True


def setup_logging() -> None:
    settings = get_settings()
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    handler = logging.StreamHandler(sys.stdout)

    if settings.log_format == "json":
        formatter = JsonFormatter(
            fmt="%(asctime)s %(levelname)s %(name)s %(message)s %(request_id)s",
            rename_fields={"asctime": "timestamp", "levelname": "level", "name": "logger"},
        )
    else:
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | [%(request_id)s] %(message)s"
        )

    handler.setFormatter(formatter)
    handler.addFilter(RequestIdFilter())
    handler.addFilter(SensitiveDataFilter())
    root.addHandler(handler)

    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.debug else logging.WARNING
    )


def generate_request_id() -> str:
    return str(uuid.uuid4())


def log_extra(**kwargs: Any) -> dict[str, Any]:
    return {"request_id": request_id_ctx.get(), **kwargs}
