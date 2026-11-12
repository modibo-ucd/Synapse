"""Tests for the error hierarchy and the central handler response shape."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.core.errors import (
    ConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
    error_response,
    register_exception_handlers,
)


def test_error_response_shape() -> None:
    body = error_response("provider_error", "upstream failed", "req-123")
    assert body == {
        "error": {
            "code": "provider_error",
            "message": "upstream failed",
            "request_id": "req-123",
        }
    }


def _make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    return app


@pytest.mark.parametrize(
    ("exc", "expected_status", "expected_code"),
    [
        (ProviderError("upstream failed"), 502, "provider_error"),
        (ProviderTimeoutError("timeout"), 504, "provider_timeout"),
        (ConfigurationError("no key"), 503, "configuration_error"),
        (RateLimitError("too fast"), 429, "rate_limited"),
    ],
)
def test_app_error_handler_status_codes(exc, expected_status, expected_code) -> None:
    app = _make_app()

    @app.get("/boom")
    async def boom() -> dict[str, str]:
        raise exc

    with TestClient(app) as client:
        resp = client.get("/boom")
    assert resp.status_code == expected_status
    body = resp.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "request_id"}
    assert body["error"]["code"] == expected_code
    assert body["error"]["message"] == str(exc)


def test_validation_error_handler_shape() -> None:
    app = _make_app()

    class Payload(BaseModel):
        name: str

    @app.post("/thing")
    async def thing(payload: Payload) -> dict[str, str]:
        return {"name": payload.name}

    with TestClient(app) as client:
        resp = client.post("/thing", json={"wrong": 1})
    assert resp.status_code == 422
    body = resp.json()
    assert body["error"]["code"] == "validation_error"
    assert set(body["error"]) == {"code", "message", "request_id"}
