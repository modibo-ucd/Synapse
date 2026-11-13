"""Tests for serving the built frontend (static assets + SPA fallback)."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main as main_module
from app.core.config import Settings
from app.main import create_app


def _write_dist(dist: Path) -> None:
    assets = dist / "assets"
    assets.mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>spa</body></html>", encoding="utf-8")
    (assets / "app.js").write_text("// app.js", encoding="utf-8")


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        _env_file=None,
        corpus_dir=str(tmp_path / "corpus"),
        cache_dir=str(tmp_path / "cache"),
    )


def test_spa_serves_index_and_assets_and_keeps_api_routes(monkeypatch, tmp_path) -> None:
    dist = tmp_path / "dist"
    _write_dist(dist)
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", dist)
    app = create_app(_settings(tmp_path))

    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert root.text == "<html><body>spa</body></html>"

        deep = client.get("/some/spa/route")
        assert deep.status_code == 200
        assert deep.text == "<html><body>spa</body></html>"

        asset = client.get("/assets/app.js")
        assert asset.status_code == 200
        assert asset.text == "// app.js"

        # API routes keep precedence over the SPA fallback.
        assert client.get("/health").status_code == 200
        assert client.get("/openapi.json").status_code == 200


def test_api_starts_without_dist(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", tmp_path / "missing-dist")
    app = create_app(_settings(tmp_path))

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/").status_code == 404


def test_spa_fallback_does_not_capture_api_or_missing_assets(monkeypatch, tmp_path) -> None:
    dist = tmp_path / "dist"
    _write_dist(dist)
    monkeypatch.setattr(main_module, "FRONTEND_DIST_DIR", dist)
    app = create_app(_settings(tmp_path))

    with TestClient(app) as client:
        # Reserved prefixes and fixed routes must not fall through to index.html.
        assert client.get("/api/unknown").status_code == 404
        assert client.get("/ask/nope").status_code == 404
        assert client.get("/docs/whatever").status_code == 404
        assert client.get("/missing.js").status_code == 404
        # Navigation-like deep routes still serve the SPA.
        assert client.get("/some/spa/route").status_code == 200
        assert client.get("/some/spa/route").text == "<html><body>spa</body></html>"
        # Fixed routes still work.
        assert client.get("/health").status_code == 200
        assert client.get("/openapi.json").status_code == 200
        assert client.get("/docs").status_code == 200
