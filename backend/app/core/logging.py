"""JSON logging to stdout with a request id carried via a ContextVar.

Secrets (the API key and the base URL) must never be passed to the logger.
"""

from __future__ import annotations

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)

# Secret values (the API key and base URL) that must never appear in any log line.
# Redaction is applied to the final serialized string, so it covers messages,
# exception tracebacks and any extra fields alike.
_REDACTED = "[REDACTED]"
_secret_values: set[str] = set()


def register_secrets(*values: str) -> None:
    """Register secret substrings to be scrubbed from every log line."""
    for value in values:
        if value:
            _secret_values.add(value)


def _redact(text: str) -> str:
    for secret in _secret_values:
        if secret in text:
            text = text.replace(secret, _REDACTED)
    return text


def get_request_id() -> str | None:
    """Return the request id for the current context, if any."""
    return request_id_var.get()


def set_request_id(request_id: str) -> None:
    """Set the request id for the current context."""
    request_id_var.set(request_id)


class JsonFormatter(logging.Formatter):
    """Format each log record as a single-line JSON object."""

    _STANDARD_KEYS = {
        "name", "msg", "args", "levelname", "levelno", "pathname", "filename", "module",
        "exc_info", "exc_text", "stack_info", "lineno", "funcName", "created", "msecs",
        "relativeCreated", "thread", "threadName", "processName", "process", "message",
        "asctime", "taskName",
    }

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": request_id_var.get(),
        }
        for key, value in record.__dict__.items():
            if key not in self._STANDARD_KEYS and not key.startswith("_"):
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return _redact(json.dumps(payload))


def configure_logging(level: str, secrets: tuple[str, ...] = ()) -> None:
    """Replace the root logger's handlers with a single JSON stdout handler.

    ``secrets`` are registered for redaction so they can never leak via messages
    or tracebacks.
    """
    register_secrets(*secrets)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level.upper())
    # Third-party HTTP clients log the full request URL (including the base URL) at
    # INFO; keep them quiet so the base URL never appears in logs.
    for name in ("httpx", "httpx2", "httpcore", "openai"):
        logging.getLogger(name).setLevel(logging.WARNING)
