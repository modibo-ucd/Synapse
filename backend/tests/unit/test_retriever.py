"""Tests for the Stage 2 Retriever (dedupe, coverage, budget, exact-term recall)."""

from __future__ import annotations

from app.retrieval.bm25 import BM25Index
from app.retrieval.hybrid import HybridSearcher
from app.retrieval.retriever import Retriever
from app.retrieval.vector_index import NumpyVectorIndex
from app.schemas.domain import Chunk, Plan, SubGoal
from tests.fakes.embeddings import FakeEmbeddingProvider


def _chunk(chunk_id: str, drug: str, text: str, token_count: int = 20) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        source_file=f"dailymed-{drug}.md",
        drug_name=drug,
        source_type="dailymed",
        section_path=f"{drug} > 4 CONTRAINDICATIONS",
        section="4 CONTRAINDICATIONS",
        text=text,
        embedding_text=f"{drug} (dailymed) {drug} > 4 CONTRAINDICATIONS\n{text}",
        index=0,
        token_count=token_count,
    )


def _retriever(
    chunks: list[Chunk],
    drugs: set[str],
    *,
    top_k: int = 5,
    token_budget: int = 10000,
    dense_available: bool = False,
) -> Retriever:
    bm25 = BM25Index([chunk.embedding_text for chunk in chunks])
    searcher = HybridSearcher(NumpyVectorIndex(), bm25, chunks, {})
    return Retriever(
        searcher,
        FakeEmbeddingProvider(),
        chunks,
        drugs,
        top_k=top_k,
        token_budget=token_budget,
        dense_available=dense_available,
    )


def _plan(*sub_goals: SubGoal) -> Plan:
    return Plan(
        complexity="multi_hop" if len(sub_goals) > 1 else "simple",
        in_scope=True,
        sub_goals=list(sub_goals),
    )


async def test_dedupe_across_sub_goals() -> None:
    chunks = [
        _chunk("w1", "warfarin", "warfarin bleeding risk"),
        _chunk("a1", "acetaminophen", "acetaminophen fever"),
    ]
    retriever = _retriever(chunks, {"warfarin", "acetaminophen"})
    plan = _plan(
        SubGoal(id="g1", question="warfarin bleeding", entities=["warfarin"]),
        SubGoal(id="g2", question="warfarin bleeding risk", entities=["warfarin"]),
    )
    evidence = await retriever.run(plan)
    ids = [chunk.chunk_id for chunk in evidence.chunks]
    assert "w1" in ids
    assert len(ids) == len(set(ids))


async def test_drug_coverage_rule() -> None:
    chunks = [
        _chunk("w1", "warfarin", "warfarin bleeding risk requires INR monitoring"),
        _chunk("w2", "warfarin", "warfarin dosage 2 to 5 mg"),
        _chunk("a1", "apixaban", "apixaban is a direct oral anticoagulant"),
        _chunk("a2", "apixaban", "apixaban bleeding side effects"),
    ]
    retriever = _retriever(chunks, {"warfarin", "apixaban"}, top_k=1)
    plan = _plan(
        SubGoal(id="g", question="warfarin bleeding", entities=["warfarin", "apixaban"])
    )
    evidence = await retriever.run(plan)
    assert {chunk.drug_name for chunk in evidence.chunks} == {"warfarin", "apixaban"}


async def test_token_budget_enforced() -> None:
    chunks = [_chunk(f"c{i}", "warfarin", f"warfarin chunk {i}", token_count=100) for i in range(5)]
    retriever = _retriever(chunks, {"warfarin"}, top_k=5, token_budget=250)
    plan = _plan(SubGoal(id="g", question="warfarin chunk", entities=["warfarin"]))
    evidence = await retriever.run(plan)
    assert 0 < len(evidence.chunks) < 5
    assert sum(chunk.token_count for chunk in evidence.chunks) <= 250


async def test_drug_coverage_survives_token_budget() -> None:
    chunks = [
        _chunk("w1", "warfarin", "warfarin bleeding risk requires INR monitoring", token_count=100),
        _chunk("w2", "warfarin", "warfarin dosage 2 to 5 mg", token_count=100),
        _chunk("a1", "apixaban", "apixaban is a direct oral anticoagulant", token_count=100),
        _chunk("a2", "apixaban", "apixaban bleeding side effects", token_count=100),
    ]
    retriever = _retriever(chunks, {"warfarin", "apixaban"}, top_k=2, token_budget=250)
    plan = _plan(
        SubGoal(id="g1", question="warfarin contraindications", entities=["warfarin"]),
        SubGoal(id="g2", question="apixaban contraindications", entities=["apixaban"]),
    )
    evidence = await retriever.run(plan)
    assert {chunk.drug_name for chunk in evidence.chunks} == {"warfarin", "apixaban"}
    assert sum(chunk.token_count for chunk in evidence.chunks) <= 250


async def test_exact_term_recall() -> None:
    chunks = [
        _chunk(
            "m1",
            "metformin",
            "metformin is contraindicated in patients with eGFR below 30 mL/minute/1.73 m2.",
        ),
        _chunk("i1", "ibuprofen", "ibuprofen may cause stomach bleeding"),
        _chunk("a1", "amoxicillin", "amoxicillin treats bacterial infections"),
        _chunk("al1", "albuterol", "albuterol relaxes airways"),
    ]
    provider = FakeEmbeddingProvider(dimension=16)
    vectors = await provider.embed_batch([chunk.embedding_text for chunk in chunks])
    vector = NumpyVectorIndex()
    vector.add([chunk.chunk_id for chunk in chunks], vectors)
    bm25 = BM25Index([chunk.embedding_text for chunk in chunks])
    searcher = HybridSearcher(vector, bm25, chunks, {})
    retriever = Retriever(
        searcher,
        provider,
        chunks,
        {"metformin"},
        top_k=4,
        token_budget=10000,
        dense_available=True,
    )
    plan = _plan(SubGoal(id="g", question="eGFR 30 mL/min", entities=["metformin"]))
    evidence = await retriever.run(plan)
    assert evidence.retrieval_mode == "hybrid"
    assert any("eGFR below 30" in chunk.text for chunk in evidence.chunks)
