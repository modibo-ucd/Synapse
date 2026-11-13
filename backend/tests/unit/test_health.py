"""Tests for GET /health."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app

OPENAI_NAMES = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")


def test_health_without_llm_config(monkeypatch, tmp_path) -> None:
    for name in OPENAI_NAMES:
        monkeypatch.delenv(name, raising=False)
    settings = Settings(
        _env_file=None,
        corpus_dir=str(tmp_path / "corpus"),
        cache_dir=str(tmp_path / "cache"),
    )
    app = create_app(settings)
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["index"] in {"building", "ready", "degraded"}
    assert body["llm_configured"] is False


def test_health_with_llm_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com")
    monkeypatch.setenv("OPENAI_MODEL", "m")
    settings = Settings(
        _env_file=None,
        corpus_dir=str(tmp_path / "corpus"),
        cache_dir=str(tmp_path / "cache"),
    )
    app = create_app(settings)
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["index"] in {"building", "ready", "degraded"}
    assert body["llm_configured"] is True


def test_health_reports_version_and_index_stats_shape(monkeypatch, tmp_path) -> None:
    for name in OPENAI_NAMES:
        monkeypatch.delenv(name, raising=False)
    settings = Settings(
        _env_file=None,
        corpus_dir=str(tmp_path / "corpus"),
        cache_dir=str(tmp_path / "cache"),
    )
    app = create_app(settings)
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["version"] == "0.1.0"
    # An empty corpus yields no chunks, so index_stats is None.
    assert body["index_stats"] is None

