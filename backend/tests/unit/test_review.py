"""Tests for the Stage 4 reviewer."""

from __future__ import annotations

from app.agent.review import Reviewer, cited_text_for, missing_numbers
from app.agent.tools.base import ToolResult
from app.schemas.domain import Claim, Draft, Evidence, EvidenceChunk, Review
from tests.fakes.llm import FakeLLMClient


def _chunk(chunk_id: str, text: str) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=chunk_id,
        source_file="dailymed-test.md",
        drug_name="test",
        source_type="dailymed",
        section_path="test > 4 CONTRAINDICATIONS",
        section="4 CONTRAINDICATIONS",
        text=text,
        token_count=10,
    )


def test_missing_numbers_verbatim() -> None:
    assert missing_numbers("eGFR below 30", "eGFR below 30 mL/min") == []
    assert missing_numbers("eGFR below 35", "eGFR below 30 mL/min") == ["35"]
    assert missing_numbers("2.5 mg", "dose 2.5 mg daily") == []


def test_cited_text_for_claim() -> None:
    claim = Claim(text="x", evidence_ids=["e1"], tool_result_ids=["t0"])
    evidence = Evidence(chunks=[_chunk("e1", "evidence text")], retrieval_mode="hybrid")
    tool_results = [
        ToolResult(tool_result_id="t0", tool="g", arguments={}, status="ok", output={"a": 1})
    ]
    cited = cited_text_for(claim, evidence, tool_results)
    assert "evidence text" in cited
    assert "tool_result_id" in cited


async def test_reviewer_flags_changed_number() -> None:
    fake = FakeLLMClient()
    fake.script_structured(Review(verdict="pass"))
    reviewer = Reviewer(fake)
    draft = Draft(claims=[Claim(text="metformin contraindicated below 35", evidence_ids=["e1"])])
    evidence = Evidence(
        chunks=[_chunk("e1", "metformin contraindicated below 30")],
        retrieval_mode="hybrid",
    )
    review = await reviewer.run(draft, evidence, [])
    assert review.verdict == "revise"
    assert any("35" in flag for flag in review.unsupported_claims)


async def test_reviewer_merges_llm_flags() -> None:
    fake = FakeLLMClient()
    fake.script_structured(
        Review(
            verdict="revise",
            unsupported_claims=["claim is unsupported"],
            ambiguity_flags=["vague dosing"],
        )
    )
    reviewer = Reviewer(fake)
    draft = Draft(claims=[Claim(text="take some", evidence_ids=["e1"])])
    evidence = Evidence(chunks=[_chunk("e1", "take 5 mg")], retrieval_mode="hybrid")
    review = await reviewer.run(draft, evidence, [])
    assert review.verdict == "revise"
    assert "claim is unsupported" in review.unsupported_claims
    assert "vague dosing" in review.ambiguity_flags


async def test_reviewer_insufficient_evidence() -> None:
    fake = FakeLLMClient()
    fake.script_structured(Review(verdict="pass"))
    reviewer = Reviewer(fake)
    review = await reviewer.run(
        Draft(claims=[]), Evidence(chunks=[], retrieval_mode="bm25_only"), []
    )
    assert review.verdict == "insufficient_evidence"
