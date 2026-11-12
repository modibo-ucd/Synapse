"""Tests for the numpy vector index."""

from __future__ import annotations

import math

from app.retrieval.vector_index import NumpyVectorIndex


def test_search_returns_top_k_by_cosine() -> None:
    index = NumpyVectorIndex()
    index.add(["a", "b", "c"], [[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    results = index.search([1.0, 0.0], k=2)
    assert [chunk_id for chunk_id, _ in results] == ["a", "c"]


def test_search_normalizes_query_and_vectors() -> None:
    index = NumpyVectorIndex()
    index.add(["a", "b"], [[2.0, 0.0], [0.0, 3.0]])
    chunk_id, score = index.search([5.0, 0.0], k=1)[0]
    assert chunk_id == "a"
    assert math.isclose(score, 1.0, rel_tol=1e-5)


def test_empty_index_search() -> None:
    index = NumpyVectorIndex()
    assert index.search([1.0, 0.0], k=5) == []


def test_zero_vector_does_not_crash() -> None:
    index = NumpyVectorIndex()
    index.add(["a"], [[0.0, 0.0]])
    assert index.search([0.0, 0.0], k=1) == [("a", 0.0)]
