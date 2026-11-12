"""Tests for IndexManager readiness, fallback and embedding cache reuse."""

from __future__ import annotations

from pathlib import Path

from app.core.config import Settings
from app.retrieval.index_manager import EmbeddingCache, IndexManager
from app.schemas.domain import Plan, SubGoal
from tests.fakes.embeddings import FakeEmbeddingProvider


def _settings(tmp_path: Path) -> Settings:
    corpus = tmp_path / "corpus"
    corpus.mkdir(exist_ok=True)
    (corpus / "dailymed-warfarin.md").write_text(
        "# Warfarin (DailyMed label)\n\n"
        "## 4 CONTRAINDICATIONS\n\n"
        "- Bleeding risk.\n\n"
        "- Hemorrhagic tendencies.\n",
        encoding="utf-8",
    )
    return Settings(
        _env_file=None,
        corpus_dir=str(corpus),
        cache_dir=str(tmp_path / "cache"),
        openai_embedding_model="text-embedding-3-small",
    )


def _plan() -> Plan:
    return Plan(
        complexity="simple",
        in_scope=True,
        sub_goals=[
            SubGoal(id="g", question="warfarin contraindications", entities=["warfarin"])
        ],
    )


class _CountingEmbeddings:
    def __init__(self, inner: FakeEmbeddingProvider) -> None:
        self._inner = inner
        self.calls = 0

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        self.calls += 1
        return await self._inner.embed_batch(texts)


async def test_build_reaches_ready(tmp_path: Path) -> None:
    manager = IndexManager(_settings(tmp_path), FakeEmbeddingProvider())
    status = await manager.await_ready(timeout=10.0)
    assert status == "ready"
    retriever = manager.retriever
    assert retriever is not None
    evidence = await retriever.run(_plan())
    assert evidence.retrieval_mode == "hybrid"
    assert any(chunk.drug_name == "warfarin" for chunk in evidence.chunks)


async def test_embedding_failure_degrades_to_bm25(tmp_path: Path) -> None:
    failing = FakeEmbeddingProvider()
    failing.script(RuntimeError("boom"))
    manager = IndexManager(_settings(tmp_path), failing)
    status = await manager.await_ready(timeout=10.0)
    assert status == "degraded"
    retriever = manager.retriever
    assert retriever is not None
    evidence = await retriever.run(_plan())
    assert evidence.retrieval_mode == "bm25_only"
    assert any(chunk.drug_name == "warfarin" for chunk in evidence.chunks)


async def test_embedding_cache_reused(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    first = _CountingEmbeddings(FakeEmbeddingProvider())
    manager1 = IndexManager(settings, first)
    assert await manager1.await_ready(timeout=10.0) == "ready"
    assert first.calls > 0

    second = _CountingEmbeddings(FakeEmbeddingProvider())
    manager2 = IndexManager(settings, second)
    assert await manager2.await_ready(timeout=10.0) == "ready"
    assert second.calls == 0


def test_embedding_cache_roundtrip(tmp_path: Path) -> None:
    cache = EmbeddingCache(tmp_path, "model-a")
    assert cache.get("k1") is None
    cache.put("k1", [0.5, 1.5])
    cache.save()
    reloaded = EmbeddingCache(tmp_path, "model-a")
    assert reloaded.get("k1") == [0.5, 1.5]
