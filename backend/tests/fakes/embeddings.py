"""Deterministic, scriptable fake embedding provider for tests.

By default it returns stable hash-based vectors so embedding consumers work
without scripting; ``script`` overrides the next call (vectors or an exception).
"""

from __future__ import annotations

import hashlib
import random

from app.providers.protocols import EmbeddingProvider


class FakeEmbeddingProvider:
    """Scriptable EmbeddingProvider with a deterministic hash-based default."""

    def __init__(self, dimension: int = 16) -> None:
        self._dimension = dimension
        self._scripts: list[list[list[float]] | Exception] = []

    def script(self, result: list[list[float]] | Exception) -> None:
        self._scripts.append(result)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self._scripts:
            item = self._scripts.pop(0)
            if isinstance(item, Exception):
                raise item
            return item
        return [self._hash_vector(text) for text in texts]

    def _hash_vector(self, text: str) -> list[float]:
        seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "big")
        rng = random.Random(seed)
        return [rng.uniform(-1.0, 1.0) for _ in range(self._dimension)]


def build_fake_embedding_provider() -> EmbeddingProvider:
    return FakeEmbeddingProvider()
