"""Tests that secrets never appear in log output."""

from __future__ import annotations

import json
import logging

from app.core.logging import JsonFormatter, register_secrets


def _format(record: logging.LogRecord) -> str:
    return JsonFormatter().format(record)


def _record(message: str, exc_info=None) -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=exc_info,
    )


def test_redacts_registered_secret_from_message() -> None:
    register_secrets("sk-verysecret")
    line = _format(_record("using key sk-verysecret to authenticate"))
    assert "sk-verysecret" not in line
    assert "[REDACTED]" in line


def test_redacts_base_url_from_message() -> None:
    register_secrets("https://proxy.internal/v1")
    line = _format(_record("request to https://proxy.internal/v1/chat failed"))
    assert "https://proxy.internal/v1" not in line
    assert "[REDACTED]" in line


def test_empty_secret_is_ignored() -> None:
    register_secrets("")
    line = _format(_record("no secrets here"))
    payload = json.loads(line)
    assert payload["message"] == "no secrets here"
