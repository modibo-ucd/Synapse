"""Tests for hybrid fusion, abbreviation expansion and rank metadata."""

from __future__ import annotations

import math

from app.retrieval.bm25 import BM25Index
from app.retrieval.hybrid import (
    HybridSearcher,
    build_abbreviation_map,
    expand_query,
    rrf_fuse,
)
from app.retrieval.vector_index import NumpyVectorIndex
from app.schemas.domain import Chunk, GlossaryEntry


def _chunk(chunk_id: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        source_file="dailymed-test.md",
        drug_name="test",
        source_type="dailymed",
        section_path="test > 4 CONTRAINDICATIONS",
        section="4 CONTRAINDICATIONS",
        text=text,
        embedding_text=f"test (dailymed) test > 4 CONTRAINDICATIONS\n{text}",
        index=0,
        token_count=10,
    )


def test_rrf_fuse_math() -> None:
    fused = rrf_fuse([["a", "b"], ["b", "a"]], k=60)
    scores = dict(fused)
    assert set(scores) == {"a", "b"}
    assert math.isclose(scores["a"], 1 / 60 + 1 / 61)
    assert math.isclose(scores["b"], 1 / 60 + 1 / 61)


def test_rrf_fuse_single_ranking() -> None:
    fused = rrf_fuse([["x", "y"]], k=60)
    assert fused == [("x", 1 / 60), ("y", 1 / 61)]


def test_abbreviation_expansion() -> None:
    entries = [
        GlossaryEntry(
            term="INR", aliases=["International Normalized Ratio"], definition="a blood test"
        )
    ]
    mapping = build_abbreviation_map(entries)
    assert mapping == {"inr": "International Normalized Ratio"}
    assert (
        expand_query("what is INR monitoring", mapping)
        == "what is INR monitoring International Normalized Ratio"
    )


def test_hybrid_search_attaches_ranks() -> None:
    chunks = [_chunk("c1", "warfarin bleeding risk"), _chunk("c2", "warfarin monitoring")]
    bm25 = BM25Index([chunk.embedding_text for chunk in chunks])
    vector = NumpyVectorIndex()
    vector.add([chunk.chunk_id for chunk in chunks], [[1.0, 0.0], [0.0, 1.0]])
    searcher = HybridSearcher(vector, bm25, chunks, {})
    hits = searcher.search("warfarin bleeding", [1.0, 0.0], top_k=2)
    by_id = {hit.chunk_id: hit for hit in hits}
    assert by_id["c1"].bm25_rank == 1
    assert by_id["c1"].dense_rank == 1
    assert by_id["c2"].bm25_rank == 2
    assert by_id["c2"].dense_rank == 2
    assert by_id["c1"].fused_score > by_id["c2"].fused_score
