"""Tests for GET /api/v1/sources (list + document + ETag + traversal)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers import openai as openai_providers
from app.retrieval.index_manager import IndexManager
from tests.fakes.embeddings import FakeEmbeddingProvider


def _corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "dailymed-warfarin.md").write_text(
        "# Warfarin (DailyMed label)\n\n"
        "## 4 CONTRAINDICATIONS\n\n"
        "warfarin is contraindicated in pregnancy. 😀\n\n"
        "## 5 WARNINGS\n\n"
        "Monitor INR.\n",
        encoding="utf-8",
    )
    (corpus / "GLOSSARY.md").write_text(
        "# Pharmacology Glossary\n\n## Core concepts\n\n"
        "- **INR**: International Normalized Ratio.\n",
        encoding="utf-8",
    )
    return corpus


def _settings(tmp_path: Path, corpus: Path) -> Settings:
    return Settings(
        _env_file=None,
        corpus_dir=str(corpus),
        cache_dir=str(tmp_path / "cache"),
    )


def test_sources_list_and_document(tmp_path) -> None:
    app = create_app(_settings(tmp_path, _corpus(tmp_path)))
    with TestClient(app) as client:
        listing = client.get("/api/v1/sources")
        assert listing.status_code == 200
        items = listing.json()
        assert {item["file_name"] for item in items} == {"dailymed-warfarin.md", "GLOSSARY.md"}

        warfarin = next(item for item in items if item["file_name"] == "dailymed-warfarin.md")
        assert warfarin["source_type"] == "dailymed"
        assert warfarin["drug_name"] == "warfarin"
        assert warfarin["size_chars"] > 0

        resp = client.get("/api/v1/sources/dailymed-warfarin.md")
        assert resp.status_code == 200
        body = resp.json()
        assert body["file_name"] == "dailymed-warfarin.md"
        assert "warfarin is contraindicated in pregnancy" in body["markdown"]
        assert body["chunks"]

        # Spans are UTF-16 code-unit offsets that slice to non-empty text.
        code_units = len(body["markdown"].encode("utf-16-le")) // 2
        for span in body["chunks"]:
            assert 0 <= span["start"] < span["end"] <= code_units
            sliced = body["markdown"].encode("utf-16-le")[
                span["start"] * 2 : span["end"] * 2
            ].decode("utf-16-le")
            assert sliced.strip()

        glossary = client.get("/api/v1/sources/GLOSSARY.md")
        assert glossary.status_code == 200
        assert glossary.json()["source_type"] == "glossary"
        assert glossary.json()["chunks"] == []

        # ETag / 304 round-trip.
        etag = resp.headers["ETag"]
        assert etag.startswith('W/"')
        cached = client.get(
            "/api/v1/sources/dailymed-warfarin.md",
            headers={"If-None-Match": etag},
        )
        assert cached.status_code == 304
        assert cached.content == b""


def test_sources_404_for_unknown_invalid_and_traversal(tmp_path) -> None:
    app = create_app(_settings(tmp_path, _corpus(tmp_path)))
    with TestClient(app) as client:
        assert client.get("/api/v1/sources/does-not-exist.md").status_code == 404
        assert client.get("/api/v1/sources/not-a-source.txt").status_code == 404
        assert client.get("/api/v1/sources/..%2F..%2Fetc%2Fpasswd").status_code == 404
        assert client.get("/api/v1/sources/..%2f..%2fetc%2fpasswd").status_code == 404
        assert client.get("/api/v1/sources/a%00b.md").status_code == 404
        assert client.get("/api/v1/sources/" + "a" * 200 + ".md").status_code == 404
        # Errors use the standard error shape.
        error_body = client.get("/api/v1/sources/does-not-exist.md").json()
        assert error_body["error"]["code"] == "not_found"


class _SlowEmbeddings:
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        await asyncio.sleep(3600)
        return []


def test_sources_work_while_index_building(monkeypatch, tmp_path) -> None:
    monkeypatch.setattr(openai_providers, "build_embedding_provider", lambda _s: _SlowEmbeddings())
    app = create_app(_settings(tmp_path, _corpus(tmp_path)))
    with TestClient(app) as client:
        assert client.get("/health").json()["index"] == "building"
        assert client.get("/api/v1/sources").status_code == 200
        assert client.get("/api/v1/sources/dailymed-warfarin.md").status_code == 200


async def test_health_index_stats_when_ready(tmp_path) -> None:
    app = create_app(_settings(tmp_path, _corpus(tmp_path)))
    manager = IndexManager(app.state.settings, FakeEmbeddingProvider())
    assert await manager.await_ready(10.0) == "ready"
    app.state.index_manager = manager

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/health")

    body = resp.json()
    assert body["version"] == "0.1.0"
    assert set(body["index_stats"]) == {"files", "chunks", "embedding_model"}
    assert body["index_stats"]["files"] == 1
    assert body["index_stats"]["embedding_model"] == "text-embedding-3-small"
