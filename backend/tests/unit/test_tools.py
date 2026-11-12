"""Tests for the local agent tools and registry."""

from __future__ import annotations

import asyncio

from pydantic import BaseModel, ConfigDict

from app.agent.tools import build_tool_registry
from app.agent.tools.base import Tool, ToolRegistry
from app.agent.tools.glossary import (
    GlossaryLookupArgs,
    GlossaryLookupResult,
    GlossaryLookupTool,
)
from app.agent.tools.label import LabelSectionArgs, LabelSectionLookupTool, LabelSectionResult
from app.agent.tools.threshold import (
    ThresholdCheckArgs,
    ThresholdCheckResult,
    ThresholdCheckTool,
    extract_threshold,
)
from app.schemas.domain import Chunk, GlossaryEntry


def _chunk(chunk_id: str, drug: str, section_path: str, text: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        source_file=f"dailymed-{drug}.md",
        drug_name=drug,
        source_type="dailymed",
        section_path=section_path,
        section=section_path.split(" > ")[-1],
        text=text,
        embedding_text=text,
        index=0,
        token_count=10,
    )


def test_build_tool_registry_registers_three_tools() -> None:
    registry = build_tool_registry([], [])
    assert registry.get("glossary_lookup") is not None
    assert registry.get("label_section_lookup") is not None
    assert registry.get("threshold_check") is not None
    assert len(registry.specs()) == 3


async def test_glossary_lookup_exact() -> None:
    tool = GlossaryLookupTool(
        [
            GlossaryEntry(
                term="INR", aliases=["International Normalized Ratio"], definition="a blood test"
            )
        ]
    )
    result = await tool.run(GlossaryLookupArgs(term="INR"))
    assert isinstance(result, GlossaryLookupResult)
    assert result.found is True
    assert result.term == "INR"
    assert result.definition == "a blood test"


async def test_glossary_lookup_fuzzy_and_not_found() -> None:
    tool = GlossaryLookupTool(
        [GlossaryEntry(term="INR", aliases=[], definition="a blood test")]
    )
    fuzzy = await tool.run(GlossaryLookupArgs(term="in"))
    assert isinstance(fuzzy, GlossaryLookupResult)
    assert fuzzy.found is True
    assert fuzzy.matched_term == "inr"

    missing = await tool.run(GlossaryLookupArgs(term="zzzz"))
    assert isinstance(missing, GlossaryLookupResult)
    assert missing.found is False


async def test_label_section_lookup() -> None:
    chunks = [
        _chunk("w1", "warfarin", "warfarin > 4 CONTRAINDICATIONS", "do not use in pregnancy"),
        _chunk("w2", "warfarin", "warfarin > 2 DOSAGE AND ADMINISTRATION", "2 to 5 mg"),
    ]
    tool = LabelSectionLookupTool(chunks)
    result = await tool.run(LabelSectionArgs(drug="warfarin", section="Contraindications"))
    assert isinstance(result, LabelSectionResult)
    assert result.found is True
    assert "4 CONTRAINDICATIONS" in result.heading_path
    assert "pregnancy" in result.text


async def test_label_section_lookup_boxed_warning_synonym() -> None:
    chunks = [_chunk("w1", "warfarin", "warfarin > WARNING: BLEEDING RISK", "major bleeding")]
    tool = LabelSectionLookupTool(chunks)
    result = await tool.run(LabelSectionArgs(drug="warfarin", section="boxed warning"))
    assert isinstance(result, LabelSectionResult)
    assert result.found is True


async def test_label_section_lookup_not_found() -> None:
    tool = LabelSectionLookupTool([])
    result = await tool.run(LabelSectionArgs(drug="warfarin", section="Contraindications"))
    assert isinstance(result, LabelSectionResult)
    assert result.found is False


def test_extract_threshold_contraindicated() -> None:
    text = "metformin is contraindicated in patients with an eGFR below 30 mL/min/1.73 m2."
    verdict, passage = extract_threshold(text, "eGFR", 25)
    assert verdict == "contraindicated"
    assert "below 30" in passage


def test_extract_threshold_not_recommended() -> None:
    text = "Initiation in patients with an eGFR between 30 to 45 mL/min is not recommended."
    verdict, _ = extract_threshold(text, "eGFR", 40)
    assert verdict == "not_recommended_to_start"


def test_extract_threshold_within_range() -> None:
    text = "maintain a target INR of 2.5 (INR range, 2.0 to 3.0)."
    verdict, _ = extract_threshold(text, "INR", 2.5)
    assert verdict == "within_range"


def test_extract_threshold_unknown_without_parameter() -> None:
    assert extract_threshold(
        "metformin is contraindicated below 30.", "eGFR", 25
    ) == ("unknown", "")


def test_extract_threshold_unknown_when_unparseable() -> None:
    assert extract_threshold("eGFR should be monitored regularly.", "eGFR", 25) == ("unknown", "")


async def test_threshold_check_tool_egfr_25() -> None:
    chunks = [
        _chunk(
            "m1",
            "metformin",
            "metformin > 4 CONTRAINDICATIONS",
            "metformin is contraindicated in patients with an eGFR below 30 mL/min/1.73 m2.",
        )
    ]
    tool = ThresholdCheckTool(chunks)
    result = await tool.run(ThresholdCheckArgs(drug="metformin", parameter="eGFR", value=25))
    assert isinstance(result, ThresholdCheckResult)
    assert result.verdict == "contraindicated"
    assert "below 30" in result.supporting_passage


async def test_threshold_check_tool_unknown_for_other_drug() -> None:
    tool = ThresholdCheckTool(
        [_chunk("m1", "metformin", "metformin > 4 CONTRAINDICATIONS", "eGFR below 30")]
    )
    result = await tool.run(ThresholdCheckArgs(drug="warfarin", parameter="eGFR", value=25))
    assert isinstance(result, ThresholdCheckResult)
    assert result.verdict == "unknown"
    assert result.found is False


async def test_registry_unknown_tool_returns_error() -> None:
    registry = ToolRegistry()
    result = await registry.execute("nope", {}, tool_result_id="t0", timeout=5.0)
    assert result.status == "error"
    assert "unknown tool" in (result.error or "")


async def test_registry_invalid_args_returns_error() -> None:
    registry = ToolRegistry()
    registry.register(GlossaryLookupTool([]))
    result = await registry.execute(
        "glossary_lookup", {"term": 123}, tool_result_id="t0", timeout=5.0
    )
    assert result.status == "error"
    assert "invalid arguments" in (result.error or "")


async def test_registry_timeout_returns_error() -> None:
    registry = ToolRegistry()
    registry.register(_SlowTool())
    result = await registry.execute("slow", {}, tool_result_id="t0", timeout=0.01)
    assert result.status == "error"
    assert result.error == "tool timed out"


class _EmptyArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _EmptyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")


class _SlowTool(Tool):
    name = "slow"
    description = "a deliberately slow tool"
    args_model = _EmptyArgs

    async def run(self, args: BaseModel) -> BaseModel:
        await asyncio.sleep(0.1)
        return _EmptyResult()

