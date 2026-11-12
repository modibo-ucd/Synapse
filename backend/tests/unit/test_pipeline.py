"""Tests for the five-stage pipeline."""

from __future__ import annotations

from app.agent.answer import Answerer
from app.agent.pipeline import Pipeline
from app.agent.plan import Planner
from app.agent.review import Reviewer
from app.agent.tool_runner import ToolRunner
from app.agent.tools.base import ToolRegistry
from app.agent.usage import TokenTrackingLLMClient
from app.core.constants import MEDICAL_DISCLAIMER
from app.providers.protocols import ToolChatResult
from app.retrieval.bm25 import BM25Index
from app.retrieval.hybrid import HybridSearcher
from app.retrieval.retriever import Retriever
from app.retrieval.vector_index import NumpyVectorIndex
from app.schemas.domain import Chunk, Claim, Draft, Plan, Review, SubGoal
from tests.fakes.embeddings import FakeEmbeddingProvider
from tests.fakes.llm import FakeLLMClient


def _chunk(chunk_id: str, drug: str, text: str) -> Chunk:
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
        token_count=20,
    )


def _build_pipeline(fake: FakeLLMClient) -> Pipeline:
    chunks = [_chunk("e1", "warfarin", "warfarin is contraindicated in pregnancy")]
    bm25 = BM25Index([chunk.embedding_text for chunk in chunks])
    searcher = HybridSearcher(NumpyVectorIndex(), bm25, chunks, {})
    retriever = Retriever(
        searcher,
        FakeEmbeddingProvider(),
        chunks,
        {"warfarin"},
        top_k=5,
        token_budget=1000,
        dense_available=False,
    )
    tracker = TokenTrackingLLMClient(fake)
    return Pipeline(
        Planner(tracker),
        retriever,
        ToolRunner(tracker, ToolRegistry()),
        Reviewer(tracker),
        Answerer(),
        usage=tracker,
    )


async def test_stage_order_and_completeness() -> None:
    fake = FakeLLMClient()
    fake.script_structured(
        Plan(
            complexity="simple",
            in_scope=True,
            sub_goals=[
                SubGoal(id="sg1", question="warfarin contraindications", entities=["warfarin"])
            ],
        )
    )
    fake.script_tools(ToolChatResult(None, []))
    fake.script_structured(
        Draft(claims=[Claim(text="warfarin contraindicated in pregnancy", evidence_ids=["e1"])])
    )
    fake.script_structured(Review(verdict="pass"))
    pipeline = _build_pipeline(fake)

    response = await pipeline.run("warfarin contraindications")

    assert [event.stage for event in pipeline.events] == [
        "plan", "retrieve", "tools", "review", "answer"
    ]
    assert all(event.status == "ok" for event in pipeline.events)
    assert "dailymed-warfarin.md" in response.answer
    assert MEDICAL_DISCLAIMER in response.answer
    assert response.plan.in_scope is True


async def test_out_of_scope_emits_all_five_events() -> None:
    fake = FakeLLMClient()
    fake.script_structured(Plan(complexity="simple", in_scope=False, sub_goals=[]))
    pipeline = _build_pipeline(fake)

    response = await pipeline.run("what is the weather today")

    assert [event.stage for event in pipeline.events] == [
        "plan", "retrieve", "tools", "review", "answer"
    ]
    assert [event.status for event in pipeline.events] == [
        "ok", "skipped", "skipped", "skipped", "skipped"
    ]
    assert "outside the scope" in response.answer
    assert MEDICAL_DISCLAIMER in response.answer
    assert response.sources == []
    assert response.citations == []
