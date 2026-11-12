"""Stage 1: decompose the question into a validated Plan."""

from __future__ import annotations

import re

from app.agent.prompts.plan import PLAN_SYSTEM_PROMPT
from app.core.constants import MAX_SUB_GOALS
from app.core.errors import AgentError
from app.providers.protocols import LLMClient, Messages
from app.schemas.domain import Plan, SubGoal

_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def sanitize_question(text: str) -> str:
    """Strip control characters and collapse whitespace."""
    return " ".join(_CONTROL_RE.sub("", text).split())


def _repair_message(max_sub_goals: int) -> str:
    return (
        "Your previous plan was invalid. For in-scope questions provide between 1 and "
        f"{max_sub_goals} sub-goals, each with a non-empty question and a unique id. "
        "Respond again with a valid Plan JSON object."
    )


class Planner:
    """Runs Stage 1 planning with structured output and semantic validation."""

    def __init__(self, llm: LLMClient, *, max_sub_goals: int = MAX_SUB_GOALS) -> None:
        self._llm = llm
        self._max_sub_goals = max_sub_goals

    async def run(self, question: str) -> Plan:
        question = sanitize_question(question)
        messages: Messages = [
            {"role": "system", "content": PLAN_SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ]
        plan = self._validate((await self._llm.generate_structured(messages, Plan)).parsed)
        if plan is None:
            messages.append({"role": "user", "content": _repair_message(self._max_sub_goals)})
            plan = self._validate((await self._llm.generate_structured(messages, Plan)).parsed)
            if plan is None:
                raise AgentError(
                    "Planner could not produce a valid plan after a repair attempt."
                )
        return plan

    def _validate(self, plan: Plan) -> Plan | None:
        if not plan.in_scope:
            return plan.model_copy(update={"sub_goals": []})
        if not plan.sub_goals or len(plan.sub_goals) > self._max_sub_goals:
            return None
        normalized: list[SubGoal] = []
        seen: set[str] = set()
        for index, sub_goal in enumerate(plan.sub_goals):
            question = sub_goal.question.strip()
            if not question:
                return None
            base = sub_goal.id.strip() or f"sg{index + 1}"
            sub_id = base
            suffix = 2
            while sub_id in seen:
                sub_id = f"{base}_{suffix}"
                suffix += 1
            seen.add(sub_id)
            normalized.append(
                SubGoal(
                    id=sub_id,
                    question=question,
                    intent=sub_goal.intent.strip(),
                    entities=sub_goal.entities,
                )
            )
        return plan.model_copy(update={"sub_goals": normalized})
