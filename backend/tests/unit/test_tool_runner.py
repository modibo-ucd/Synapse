"""Tests for the Stage 3 tool runner."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.agent.tool_runner import ToolRunner, clean_draft
from app.agent.tools.base import Tool, ToolRegistry
from app.providers.protocols import ToolCall, ToolChatResult
from app.schemas.domain import Claim, Draft, Evidence, EvidenceChunk, Plan, SubGoal
from tests.fakes.llm import FakeLLMClient


class SpyArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str


class SpyResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    echoed: str


class _SpyBase(Tool):
    description = "spy tool"
    args_model = SpyArgs

    def __init__(self, log: list[str]) -> None:
        self._log = log

    async def run(self, args: BaseModel) -> BaseModel:
        assert isinstance(args, SpyArgs)
        self._log.append(self.name)
        return SpyResult(echoed=args.key)


class SpyATool(_SpyBase):
    name = "spy_a"


class SpyBTool(_SpyBase):
    name = "spy_b"


class _BoomTool(Tool):
    name = "boom"
    description = "a tool that always fails"
    args_model = SpyArgs

    async def run(self, args: BaseModel) -> BaseModel:
        raise ValueError("boom")


def _plan() -> Plan:
    return Plan(
        complexity="simple",
        in_scope=True,
        sub_goals=[SubGoal(id="sg1", question="q", entities=[])],
    )


def _evidence() -> Evidence:
    return Evidence(chunks=[_evidence_chunk("e1")], retrieval_mode="hybrid")


def _evidence_chunk(chunk_id: str) -> EvidenceChunk:
    return EvidenceChunk(
        chunk_id=chunk_id,
        source_file="dailymed-test.md",
        drug_name="test",
        source_type="dailymed",
        section_path="test > 4 CONTRAINDICATIONS",
        section="4 CONTRAINDICATIONS",
        text="some evidence text",
        token_count=5,
    )


async def test_dynamic_tool_dispatch() -> None:
    log: list[str] = []
    registry = ToolRegistry()
    registry.register(SpyATool(log))
    registry.register(SpyBTool(log))
    llm = FakeLLMClient()
    runner = ToolRunner(llm, registry)

    llm.script_tools(ToolChatResult(None, [ToolCall("spy_a", {"key": "x"})]))
    llm.script_tools(ToolChatResult(None, []))
    llm.script_structured(Draft(claims=[], markdown="a"))
    await runner.run(_plan(), _evidence())

    llm.script_tools(ToolChatResult(None, [ToolCall("spy_b", {"key": "y"})]))
    llm.script_tools(ToolChatResult(None, []))
    llm.script_structured(Draft(claims=[], markdown="b"))
    await runner.run(_plan(), _evidence())

    assert log == ["spy_a", "spy_b"]


async def test_no_tools_needed() -> None:
    registry = ToolRegistry()
    llm = FakeLLMClient()
    llm.script_tools(ToolChatResult(None, []))
    llm.script_structured(Draft(claims=[], markdown="no tools"))
    runner = ToolRunner(llm, registry)
    draft = await runner.run(_plan(), _evidence())
    assert draft.markdown == "no tools"


async def test_tool_error_reported_as_result() -> None:
    registry = ToolRegistry()
    registry.register(_BoomTool())
    llm = FakeLLMClient()
    llm.script_tools(ToolChatResult(None, [ToolCall("boom", {"key": "x"})]))
    llm.script_tools(ToolChatResult(None, []))
    llm.script_structured(
        Draft(claims=[Claim(text="claim", tool_result_ids=["t0"])], markdown="x")
    )
    runner = ToolRunner(llm, registry)
    draft = await runner.run(_plan(), _evidence())
    assert [claim.text for claim in draft.claims] == ["claim"]


def test_clean_draft_drops_unreferenced_and_invalid() -> None:
    draft = Draft(
        claims=[
            Claim(text="good", evidence_ids=["e1"]),
            Claim(text="bad-ref", evidence_ids=["nope"]),
            Claim(text="unreferenced"),
        ],
        markdown="m",
    )
    cleaned, changed = clean_draft(draft, {"e1"}, {"t0"})
    assert changed is True
    assert [claim.text for claim in cleaned.claims] == ["good"]


async def test_claim_reference_validation_repairs() -> None:
    registry = ToolRegistry()
    llm = FakeLLMClient()
    llm.script_tools(ToolChatResult(None, []))
    llm.script_structured(
        Draft(
            claims=[
                Claim(text="ok", evidence_ids=["e1"]),
                Claim(text="unreferenced"),
            ],
            markdown="x",
        )
    )
    llm.script_structured(Draft(claims=[Claim(text="ok", evidence_ids=["e1"])], markdown="x"))
    runner = ToolRunner(llm, registry)
    draft = await runner.run(_plan(), _evidence())
    assert [claim.text for claim in draft.claims] == ["ok"]
