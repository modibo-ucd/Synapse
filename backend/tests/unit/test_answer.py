"""Tests for the Stage 5 answerer."""

from __future__ import annotations

from app.agent.answer import Answerer
from app.agent.tools.base import ToolResult
from app.core.constants import MEDICAL_DISCLAIMER
from app.schemas.domain import Claim, Draft, Evidence, EvidenceChunk, Review


def _chunk(chunk_id: str, source_file: str, section: str, text: str) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=chunk_id,
        source_file=source_file,
        drug_name="test",
        source_type="dailymed",
        section_path=f"test > {section}",
        section=section,
        text=text,
        token_count=10,
    )


def _evidence() -> Evidence:
    return Evidence(
        chunks=[
            _chunk(
                "e1", "dailymed-warfarin.md", "4 CONTRAINDICATIONS",
                "warfarin is contraindicated in pregnancy",
            )
        ],
        retrieval_mode="hybrid",
    )


async def test_disclaimer_always_present() -> None:
    answerer = Answerer()
    assembly = await answerer.run(
        Draft(claims=[Claim(text="warfarin contraindicated in pregnancy", evidence_ids=["e1"])]),
        Review(verdict="pass"),
        _evidence(),
        [],
    )
    assert MEDICAL_DISCLAIMER in assembly.answer
    assert assembly.disclaimer == MEDICAL_DISCLAIMER


async def test_file_names_present_in_answer() -> None:
    answerer = Answerer()
    assembly = await answerer.run(
        Draft(claims=[Claim(text="x", evidence_ids=["e1"])]),
        Review(verdict="pass"),
        _evidence(),
        [],
    )
    assert "dailymed-warfarin.md" in assembly.answer
    assert assembly.sources == ["dailymed-warfarin.md"]


async def test_unsupported_claim_removed() -> None:
    answerer = Answerer()
    draft = Draft(
        claims=[
            Claim(text="metformin contraindicated below 35", evidence_ids=["e1"]),
            Claim(text="warfarin contraindicated in pregnancy", evidence_ids=["e1"]),
        ]
    )
    assembly = await answerer.run(draft, Review(verdict="revise"), _evidence(), [])
    assert "below 35" not in assembly.answer
    assert "pregnancy" in assembly.answer


async def test_insufficient_evidence_path() -> None:
    answerer = Answerer()
    assembly = await answerer.run(
        Draft(claims=[]),
        Review(verdict="insufficient_evidence"),
        Evidence(chunks=[], retrieval_mode="bm25_only"),
        [],
    )
    assert "insufficient evidence" in assembly.answer.lower()
    assert MEDICAL_DISCLAIMER in assembly.answer


async def test_invalid_citation_dropped() -> None:
    answerer = Answerer()
    draft = Draft(claims=[Claim(text="x", evidence_ids=["does-not-exist"])])
    assembly = await answerer.run(draft, Review(verdict="pass"), _evidence(), [])
    assert assembly.citations == []
    assert "x" not in assembly.answer


async def test_citations_map_to_chunks() -> None:
    answerer = Answerer()
    draft = Draft(claims=[Claim(text="warfarin contraindicated in pregnancy", evidence_ids=["e1"])])
    assembly = await answerer.run(draft, Review(verdict="pass"), _evidence(), [])
    assert [citation.id for citation in assembly.citations] == ["S1"]
    assert assembly.citations[0].chunk_id == "e1"
    assert assembly.citations[0].source_file == "dailymed-warfarin.md"


async def test_tool_result_produces_citation() -> None:
    answerer = Answerer()
    tool_result = ToolResult(
        tool_result_id="t0",
        tool="label_section_lookup",
        arguments={"drug": "apixaban", "section": "contraindications"},
        status="ok",
        output={
            "source_file": "dailymed-apixaban.md",
            "section": "4 CONTRAINDICATIONS",
            "text": "active pathological bleeding",
        },
    )
    draft = Draft(
        claims=[
            Claim(
                text="apixaban contraindicated in active pathological bleeding",
                tool_result_ids=["t0"],
            )
        ]
    )
    assembly = await answerer.run(draft, Review(verdict="pass"), _evidence(), [tool_result])
    assert assembly.sources == ["dailymed-apixaban.md"]
    assert "dailymed-apixaban.md" in assembly.answer
    assert [citation.source_file for citation in assembly.citations] == ["dailymed-apixaban.md"]
