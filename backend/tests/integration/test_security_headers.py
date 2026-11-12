"""Security headers are present on every response (API and static)."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import SECURITY_HEADERS, create_app


def _app(tmp_path):
    settings = Settings(
        _env_file=None,
        corpus_dir=str(tmp_path / "corpus"),
        cache_dir=str(tmp_path / "cache"),
    )
    return create_app(settings)


def test_security_headers_on_api_and_docs(tmp_path) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        for path in ("/health", "/openapi.json", "/ask"):
            if path == "/ask":
                resp = client.post(path, json={"question": "warfarin contraindications"})
            else:
                resp = client.get(path)
            assert resp.status_code in {200, 503}, path
            for name, value in SECURITY_HEADERS.items():
                assert resp.headers.get(name) == value, (path, name)


def test_security_headers_block_framing_and_sniffing(tmp_path) -> None:
    app = _app(tmp_path)
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert "frame-ancestors 'none'" in resp.headers["Content-Security-Policy"]
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert resp.headers["Referrer-Policy"] == "no-referrer"
