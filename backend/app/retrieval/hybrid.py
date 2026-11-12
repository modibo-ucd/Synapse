"""Hybrid retrieval: dense + BM25 fused with reciprocal rank fusion.

Glossary-based abbreviation expansion runs before lexical search so a query like
``INR`` also matches chunks that spell out "International Normalized Ratio".
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from app.retrieval.bm25 import BM25Index, tokenize
from app.retrieval.vector_index import VectorIndex
from app.schemas.domain import Chunk, EvidenceChunk, GlossaryEntry

RRF_K = 60


def rrf_fuse(rankings: Sequence[Sequence[str]], k: int = RRF_K) -> list[tuple[str, float]]:
    """Fuse ranked id lists with reciprocal rank fusion.

    ``score(doc) = sum over lists of 1 / (k + rank)`` with a 0-based rank.
    Returns ``(doc_id, score)`` pairs sorted by descending score.
    """
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking):
            scores[doc_id] = scores.get(doc_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def build_abbreviation_map(entries: list[GlossaryEntry]) -> dict[str, str]:
    """Map the shortest name of each glossary term to its longest name.

    E.g. ``INR (International Normalized Ratio)`` -> ``{"inr": "International
    Normalized Ratio"}``.
    """
    mapping: dict[str, str] = {}
    for entry in entries:
        names = [name for name in (entry.term, *entry.aliases) if name]
        if not names:
            continue
        short = min(names, key=len)
        long = max(names, key=len)
        if short.lower() != long.lower():
            mapping[short.lower()] = long
    return mapping


def expand_query(query: str, abbreviations: Mapping[str, str]) -> str:
    """Append glossary expansions for abbreviations found in the query."""
    expansions: list[str] = []
    seen: set[str] = set()
    for token in tokenize(query):
        expansion = abbreviations.get(token)
        if expansion is not None and expansion.lower() not in seen:
            seen.add(expansion.lower())
            expansions.append(expansion)
    if not expansions:
        return query
    return f"{query} {' '.join(expansions)}"


class HybridSearcher:
    """Combines a dense index and a BM25 index over the same ordered chunks."""

    def __init__(
        self,
        vector_index: VectorIndex,
        bm25: BM25Index,
        chunks: list[Chunk],
        abbreviation_map: Mapping[str, str],
        *,
        rrf_k: int = RRF_K,
    ) -> None:
        self._vector = vector_index
        self._bm25 = bm25
        self._chunks = chunks
        self._by_id = {chunk.chunk_id: chunk for chunk in chunks}
        self._abbrev = abbreviation_map
        self._rrf_k = rrf_k

    @property
    def dense_available(self) -> bool:
        return len(self._vector) > 0

    def search(
        self, query: str, query_vector: list[float] | None, top_k: int
    ) -> list[EvidenceChunk]:
        """Hybrid search; pass ``query_vector=None`` for BM25-only ranking."""
        expanded = expand_query(query, self._abbrev)
        dense: list[tuple[str, float]] = []
        if query_vector is not None and self.dense_available:
            dense = self._vector.search(query_vector, top_k)
        lexical = self._bm25.search(expanded, top_k)
        dense_ids = [chunk_id for chunk_id, _ in dense]
        bm25_ids = [self._chunks[index].chunk_id for index, _ in lexical]
        return self._fuse(dense_ids, bm25_ids, top_k)

    def search_lexical(self, query: str, top_k: int) -> list[EvidenceChunk]:
        """BM25-only ranking (used by the drug-coverage rule)."""
        expanded = expand_query(query, self._abbrev)
        lexical = self._bm25.search(expanded, top_k)
        bm25_ids = [self._chunks[index].chunk_id for index, _ in lexical]
        return self._fuse([], bm25_ids, top_k)

    def _fuse(self, dense_ids: list[str], bm25_ids: list[str], top_k: int) -> list[EvidenceChunk]:
        rankings: list[list[str]] = [dense_ids, bm25_ids] if dense_ids else [bm25_ids]
        dense_rank = {chunk_id: rank + 1 for rank, chunk_id in enumerate(dense_ids)}
        bm25_rank = {chunk_id: rank + 1 for rank, chunk_id in enumerate(bm25_ids)}
        hits: list[EvidenceChunk] = []
        for chunk_id, score in rrf_fuse(rankings, self._rrf_k)[:top_k]:
            chunk = self._by_id[chunk_id]
            hits.append(
                EvidenceChunk(
                    chunk_id=chunk.chunk_id,
                    source_file=chunk.source_file,
                    drug_name=chunk.drug_name,
                    source_type=chunk.source_type,
                    section_path=chunk.section_path,
                    section=chunk.section,
                    text=chunk.text,
                    token_count=chunk.token_count,
                    dense_rank=dense_rank.get(chunk_id),
                    bm25_rank=bm25_rank.get(chunk_id),
                    fused_score=score,
                )
            )
        return hits
