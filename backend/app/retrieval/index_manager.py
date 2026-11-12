"""Background index building and readiness management.

Builds the BM25 + dense indices in a background task so ``/health`` can return
immediately and ``/ask`` can await readiness with a bounded wait. Embeddings are
cached on disk keyed by ``sha256(text)`` + model name. If embeddings are
unavailable the index degrades gracefully to BM25-only and never crashes.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path

from app.core.config import Settings
from app.providers.protocols import EmbeddingProvider
from app.retrieval.bm25 import BM25Index
from app.retrieval.chunker import chunk_documents
from app.retrieval.hybrid import HybridSearcher, build_abbreviation_map
from app.retrieval.loader import load_documents, load_glossary
from app.retrieval.retriever import Retriever
from app.retrieval.vector_index import NumpyVectorIndex

logger = logging.getLogger(__name__)


class EmbeddingCache:
    """On-disk cache of embedding vectors keyed by ``sha256(text)``."""

    def __init__(self, cache_dir: Path, model: str) -> None:
        digest = hashlib.sha256(model.encode()).hexdigest()[:12]
        self._path = cache_dir / f"embeddings-{digest}.json"
        self._vectors: dict[str, list[float]] = {}
        self._load()

    def _load(self) -> None:
        if not self._path.is_file():
            return
        try:
            raw = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(raw, dict):
            return
        vectors = raw.get("vectors", {})
        if not isinstance(vectors, dict):
            return
        for key, value in vectors.items():
            if isinstance(key, str) and isinstance(value, list):
                try:
                    self._vectors[key] = [float(x) for x in value]
                except (TypeError, ValueError):
                    continue

    def get(self, key: str) -> list[float] | None:
        return self._vectors.get(key)

    def put(self, key: str, vector: list[float]) -> None:
        self._vectors[key] = vector

    def save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"vectors": self._vectors}), encoding="utf-8")


class _NullEmbeddings:
    """EmbeddingProvider stand-in that fails loudly (used when none is injected)."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        raise RuntimeError("no embedding provider configured")


class IndexManager:
    """Builds the in-memory index in a background task and reports readiness."""

    def __init__(
        self, settings: Settings, embedding_provider: EmbeddingProvider | None = None
    ) -> None:
        self._settings = settings
        self._embedding: EmbeddingProvider = embedding_provider or _NullEmbeddings()
        self._status = "building"
        self._task: asyncio.Task[None] | None = None
        self._retriever: Retriever | None = None
        self._drug_names: set[str] = set()

    @property
    def status(self) -> str:
        return self._status

    @property
    def retriever(self) -> Retriever | None:
        return self._retriever

    @property
    def drug_names(self) -> set[str]:
        return self._drug_names

    def start(self) -> None:
        """Kick off the build as a background task (used by the app lifespan)."""
        if self._task is None:
            self._task = asyncio.create_task(self._build())

    async def await_ready(self, timeout: float) -> str:
        """Wait (bounded) for the build to finish and return the status."""
        if self._task is None:
            await self._build()
            return self._status
        try:
            await asyncio.wait_for(asyncio.shield(self._task), timeout)
        except (TimeoutError, asyncio.CancelledError):
            pass
        return self._status

    async def shutdown(self) -> None:
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _build(self) -> None:
        self._status = "building"
        try:
            documents = load_documents(Path(self._settings.corpus_dir))
            chunks = chunk_documents(
                documents,
                max_tokens=self._settings.chunk_max_tokens,
                overlap_tokens=self._settings.chunk_overlap_tokens,
                chars_per_token=self._settings.chars_per_token,
            )
        except Exception:  # noqa: BLE001 - a broken corpus must not crash the app
            logger.exception("Corpus loading/chunking failed; index degraded")
            self._retriever = None
            self._drug_names = set()
            self._status = "degraded"
            return

        glossary = load_glossary(Path(self._settings.corpus_dir))
        bm25 = BM25Index([chunk.embedding_text for chunk in chunks])
        abbreviations = build_abbreviation_map(glossary)
        self._drug_names = {chunk.drug_name for chunk in chunks}

        vector_index = NumpyVectorIndex()
        dense_ok = False
        try:
            vectors = await self._embed_texts([chunk.embedding_text for chunk in chunks])
            if vectors:
                vector_index.add([chunk.chunk_id for chunk in chunks], vectors)
                dense_ok = True
        except Exception:  # noqa: BLE001 - degrade to BM25-only on embedding failure
            logger.exception("Embeddings unavailable; falling back to BM25-only")

        searcher = HybridSearcher(
            vector_index, bm25, chunks, abbreviations, rrf_k=self._settings.rrf_k
        )
        self._retriever = Retriever(
            searcher,
            self._embedding,
            chunks,
            self._drug_names,
            top_k=self._settings.retrieval_top_k,
            token_budget=self._settings.retrieval_token_budget,
            dense_available=dense_ok,
        )
        self._status = "ready" if dense_ok else "degraded"

    async def _embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed texts using the disk cache; only missing texts hit the provider."""
        if not texts:
            return []
        cache = EmbeddingCache(
            Path(self._settings.cache_dir), self._settings.openai_embedding_model
        )
        keys = [hashlib.sha256(text.encode()).hexdigest() for text in texts]
        missing = [
            (text, key)
            for text, key in zip(texts, keys, strict=True)
            if cache.get(key) is None
        ]
        if missing:
            embedded = await self._embedding.embed_batch([text for text, _ in missing])
            for (_, key), vector in zip(missing, embedded, strict=True):
                cache.put(key, vector)
            cache.save()

        vectors: list[list[float]] = []
        for key in keys:
            stored = cache.get(key)
            if stored is None:
                raise RuntimeError("embedding cache incomplete after embedding")
            vectors.append(stored)
        return vectors

