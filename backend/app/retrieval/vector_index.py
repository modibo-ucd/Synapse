"""In-memory dense vector index (numpy) behind a swappable Protocol."""

from __future__ import annotations

from typing import Protocol

import numpy as np
from numpy.typing import NDArray


class VectorIndex(Protocol):
    """Minimal interface for a dense nearest-neighbour store (swappable)."""

    def add(self, ids: list[str], vectors: list[list[float]]) -> None: ...

    def search(self, query: list[float], k: int) -> list[tuple[str, float]]: ...

    def __len__(self) -> int: ...


class NumpyVectorIndex:
    """Cosine-similarity index backed by an L2-normalized float32 matrix."""

    def __init__(self) -> None:
        self._ids: list[str] = []
        self._matrix: NDArray[np.float32] = np.empty((0, 0), dtype=np.float32)

    def add(self, ids: list[str], vectors: list[list[float]]) -> None:
        if not vectors:
            return
        matrix: NDArray[np.float32] = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        matrix = matrix / norms
        if len(self._ids) == 0:
            self._matrix = matrix
        else:
            self._matrix = np.vstack([self._matrix, matrix])
        self._ids.extend(ids)

    def __len__(self) -> int:
        return len(self._ids)

    def search(self, query: list[float], k: int) -> list[tuple[str, float]]:
        """Return the top-k ``(id, cosine_score)`` pairs closest to the query."""
        if not self._ids or k <= 0:
            return []
        vector: NDArray[np.float32] = np.asarray(query, dtype=np.float32)
        norm = float(np.linalg.norm(vector))
        if norm != 0.0:
            vector = vector / norm
        scores: NDArray[np.float32] = self._matrix @ vector
        if k >= len(scores):
            order = np.argsort(scores)[::-1]
        else:
            partition = np.argpartition(scores, -k)[-k:]
            order = partition[np.argsort(scores[partition])[::-1]]
        return [(self._ids[int(i)], float(scores[int(i)])) for i in order[:k]]
