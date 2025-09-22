"""Structured logging utilities for the LLMHIVE service."""
from __future__ import annotations

import json
import logging
import sys

REQUEST_ID_FIELD = "request_id"


class JsonFormatter(logging.Formatter):
    """Serialize log records as JSON for easier ingestion."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: D401 - docstring inherited
        base = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            base["exc_info"] = self.formatException(record.exc_info)
        extra = {
            key: value
            for key, value in record.__dict__.items()
            if key not in logging.LogRecord.__dict__ and not key.startswith("_")
        }
        base.update(extra)
        return json.dumps(base, default=str)


def configure_logging() -> None:
    """Configure application wide logging handlers."""

    root = logging.getLogger()
    if getattr(configure_logging, "_configured", False):
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root.setLevel(logging.INFO)
    root.addHandler(handler)

    configure_logging._configured = True
