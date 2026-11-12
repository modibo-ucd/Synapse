"""Tests for the Stage 1 planner."""

from __future__ import annotations

import pytest

from app.agent.plan import Planner, sanitize_question
from app.core.errors import AgentError
from app.schemas.domain import Plan, SubGoal
from tests.fakes.llm import FakeLLMClient


def _sub(goal_id: str, question: str, entities: list[str] | None = None) -> SubGoal:
    return SubGoal(id=goal_id, question=question, intent="", entities=entities or [])


def test_sanitize_question_strips_control_chars() -> None:
    assert sanitize_question("hello\x00world") == "helloworld"
    assert sanitize_question("  warfarin\tcontraindications\n") == "warfarin contraindications"


async def test_plan_passes_through_valid_plan() -> None:
    fake = FakeLLMClient()
    fake.script_structured(
        Plan(
            complexity="simple",
            in_scope=True,
            sub_goals=[_sub("sg1", "warfarin contraindications", ["warfarin"])],
        )
    )
    plan = await Planner(fake).run("What are warfarin contraindications?")
    assert plan.in_scope is True
    assert [sg.id for sg in plan.sub_goals] == ["sg1"]


async def test_out_of_scope_plan_normalizes_empty_sub_goals() -> None:
    fake = FakeLLMClient()
    fake.script_structured(Plan(complexity="simple", in_scope=False, sub_goals=[]))
    plan = await Planner(fake).run("What is the weather today?")
    assert plan.in_scope is False
    assert plan.sub_goals == []


async def test_multi_drug_plan_validated() -> None:
    fake = FakeLLMClient()
    fake.script_structured(
        Plan(
            complexity="multi_hop",
            in_scope=True,
            sub_goals=[
                _sub("sg1", "warfarin contraindications", ["warfarin"]),
                _sub("sg2", "apixaban contraindications", ["apixaban"]),
                _sub("sg3", "compare them", ["warfarin", "apixaban"]),
            ],
        )
    )
    plan = await Planner(fake).run("Compare warfarin and apixaban contraindications.")
    assert len(plan.sub_goals) == 3


async def test_invalid_plan_repairs_once() -> None:
    fake = FakeLLMClient()
    fake.script_structured(Plan(complexity="simple", in_scope=True, sub_goals=[]))
    fake.script_structured(
        Plan(complexity="simple", in_scope=True, sub_goals=[_sub("sg1", "warfarin", ["warfarin"])])
    )
    plan = await Planner(fake).run("warfarin contraindications")
    assert len(plan.sub_goals) == 1


async def test_invalid_plan_raises_after_repair() -> None:
    fake = FakeLLMClient()
    fake.script_structured(Plan(complexity="simple", in_scope=True, sub_goals=[]))
    fake.script_structured(Plan(complexity="simple", in_scope=True, sub_goals=[]))
    with pytest.raises(AgentError):
        await Planner(fake).run("warfarin contraindications")
