"""Stage 2 retriever: hybrid search over sub-goals with dedupe and budgets."""

from __future__ import annotations

import asyncio

from app.providers.protocols import EmbeddingProvider
from app.retrieval.hybrid import HybridSearcher
from app.schemas.domain import Chunk, Evidence, EvidenceChunk, Plan, RetrievalMode, SubGoal


class Retriever:
    """Runs Stage 2 retrieval for a plan and assembles the Evidence output."""

    def __init__(
        self,
        searcher: HybridSearcher,
        embedding_provider: EmbeddingProvider,
        chunks: list[Chunk],
        corpus_drugs: set[str],
        *,
        top_k: int,
        token_budget: int,
        dense_available: bool,
    ) -> None:
        self._searcher = searcher
        self._embedding = embedding_provider
        self._chunks = chunks
        self._corpus_drugs = corpus_drugs
        self._top_k = top_k
        self._token_budget = token_budget
        self._dense_available = dense_available

    async def run(self, plan: Plan) -> Evidence:
        """Retrieve for every sub-goal in parallel, then dedupe and budget."""
        per_goal = await asyncio.gather(*(self._retrieve_goal(g) for g in plan.sub_goals))
        seen: set[str] = set()
        selected: list[EvidenceChunk] = []
        used_tokens = 0
        for goal_results in per_goal:
            for chunk in goal_results:
                if chunk.chunk_id in seen:
                    continue
                if selected and used_tokens + chunk.token_count > self._token_budget:
                    continue
                seen.add(chunk.chunk_id)
                selected.append(chunk)
                used_tokens += chunk.token_count
        mode: RetrievalMode = "hybrid" if self._dense_available else "bm25_only"
        return Evidence(chunks=selected, retrieval_mode=mode)

    async def _retrieve_goal(self, sub_goal: SubGoal) -> list[EvidenceChunk]:
        query_vector: list[float] | None = None
        if self._dense_available:
            try:
                vectors = await self._embedding.embed_batch([sub_goal.question])
                query_vector = vectors[0]
            except Exception:  # noqa: BLE001 - degrade this goal to lexical only
                query_vector = None
        results = self._searcher.search(sub_goal.question, query_vector, self._top_k)

        existing_ids = {chunk.chunk_id for chunk in results}
        for drug in self._named_drugs(sub_goal):
            if any(chunk.drug_name == drug for chunk in results):
                continue
            extra = self._top_chunk_for_drug(sub_goal.question, drug)
            if extra is not None and extra.chunk_id not in existing_ids:
                results.append(extra)
                existing_ids.add(extra.chunk_id)
        return results

    def _named_drugs(self, sub_goal: SubGoal) -> set[str]:
        names = {name.strip().lower() for name in sub_goal.entities if name.strip()}
        return {drug for drug in self._corpus_drugs if drug in names}

    def _top_chunk_for_drug(self, question: str, drug: str) -> EvidenceChunk | None:
        ranked = self._searcher.search_lexical(question, len(self._chunks))
        for chunk in ranked:
            if chunk.drug_name == drug:
                return chunk
        return None
