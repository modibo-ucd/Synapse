"""Pipeline stage events and the ordered, timed execution context."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict

from app.core.errors import AgentError
from app.schemas.domain import Draft, Evidence, Plan, Review

StageName = Literal["plan", "retrieve", "tools", "review", "answer"]
_ORDER: tuple[StageName, ...] = ("plan", "retrieve", "tools", "review", "answer")

T = TypeVar("T")


class StageEvent(BaseModel):
    """A typed record of one pipeline stage's execution."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: StageName
    status: Literal["ok", "skipped"]
    duration_ms: float
    summary: str = ""


class PipelineContext:
    """Runs stages in strict order, timing each and emitting a StageEvent."""

    def __init__(self) -> None:
        self._events: list[StageEvent] = []
        self._index = 0

    @property
    def events(self) -> list[StageEvent]:
        return list(self._events)

    async def run_stage(
        self, name: StageName, fn: Callable[..., Awaitable[T]], *args: Any
    ) -> T:
        self._check_order(name)
        start = time.perf_counter()
        result = await fn(*args)
        duration_ms = (time.perf_counter() - start) * 1000
        self._events.append(
            StageEvent(
                stage=name,
                status="ok",
                duration_ms=duration_ms,
                summary=_summary(name, result),
            )
        )
        return result

    def skip(self, name: StageName, summary: str = "skipped") -> None:
        self._check_order(name)
        self._events.append(
            StageEvent(stage=name, status="skipped", duration_ms=0.0, summary=summary)
        )

    def _check_order(self, name: StageName) -> None:
        if self._index >= len(_ORDER) or name != _ORDER[self._index]:
            raise AgentError(
                f"stage order violation: expected {_ORDER[self._index]!r}, got {name!r}"
            )
        self._index += 1


def _summary(name: StageName, result: object) -> str:
    if name == "plan" and isinstance(result, Plan):
        return f"{result.complexity}, {len(result.sub_goals)} sub-goal(s)"
    if name == "retrieve" and isinstance(result, Evidence):
        return f"{len(result.chunks)} chunk(s) ({result.retrieval_mode})"
    if name == "tools" and isinstance(result, Draft):
        return f"{len(result.claims)} claim(s)"
    if name == "review" and isinstance(result, Review):
        return result.verdict
    return "ok"
