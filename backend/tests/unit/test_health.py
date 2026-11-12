"""Tests for GET /health."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

OPENAI_NAMES = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")


def test_health_without_llm_config(monkeypatch) -> None:
    for name in OPENAI_NAMES:
        monkeypatch.delenv(name, raising=False)
    app = create_app(Settings(_env_file=None))
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["index"] == "building"
    assert body["llm_configured"] is False


def test_health_with_llm_config(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com")
    monkeypatch.setenv("OPENAI_MODEL", "m")
    app = create_app(Settings(_env_file=None))
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["index"] == "building"
    assert body["llm_configured"] is True
