"""Pipeline stage events and the ordered, timed execution context."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field

from app.core.errors import AgentError
from app.schemas.domain import AnswerAssembly, Draft, Evidence, Plan, Review

StageName = Literal["plan", "retrieve", "tools", "review", "answer"]
_ORDER: tuple[StageName, ...] = ("plan", "retrieve", "tools", "review", "answer")

T = TypeVar("T")


class StageEvent(BaseModel):
    """A typed record of one pipeline stage's execution.

    ``summary`` is a short human-readable string; ``details`` carries UI-safe
    structured data (sub-goals, retrieved sources, tool calls, review verdict).
    Neither ever contains prompts, keys, or other secrets.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    stage: StageName
    status: Literal["ok", "skipped"]
    duration_ms: float
    summary: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class PipelineContext:
    """Runs stages in strict order, timing each and emitting a StageEvent."""

    def __init__(
        self, on_event: Callable[[StageEvent], Awaitable[None]] | None = None
    ) -> None:
        self._events: list[StageEvent] = []
        self._index = 0
        self._on_event = on_event

    @property
    def events(self) -> list[StageEvent]:
        return list(self._events)

    async def run_stage(
        self,
        name: StageName,
        fn: Callable[..., Awaitable[T]],
        *args: Any,
        details_fn: Callable[[T], dict[str, Any]] | None = None,
    ) -> T:
        self._check_order(name)
        start = time.perf_counter()
        result = await fn(*args)
        duration_ms = (time.perf_counter() - start) * 1000
        details = details_fn(result) if details_fn is not None else _details(name, result)
        await self._emit(
            StageEvent(
                stage=name,
                status="ok",
                duration_ms=duration_ms,
                summary=_summary(name, result),
                details=details,
            )
        )
        return result

    async def skip(self, name: StageName, summary: str = "skipped") -> None:
        self._check_order(name)
        await self._emit(
            StageEvent(stage=name, status="skipped", duration_ms=0.0, summary=summary)
        )

    async def _emit(self, event: StageEvent) -> None:
        self._events.append(event)
        if self._on_event is not None:
            await self._on_event(event)

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
        files = len({chunk.source_file for chunk in result.chunks})
        return f"{len(result.chunks)} chunk(s) from {files} file(s) ({result.retrieval_mode})"
    if name == "tools" and isinstance(result, Draft):
        return f"{len(result.claims)} claim(s)"
    if name == "review" and isinstance(result, Review):
        return result.verdict
    if name == "answer" and isinstance(result, AnswerAssembly):
        return f"{len(result.sources)} source(s) cited"
    return "ok"


def _details(name: StageName, result: object) -> dict[str, Any]:
    if name == "plan" and isinstance(result, Plan):
        return {
            "complexity": result.complexity,
            "in_scope": result.in_scope,
            "sub_goals": [
                {"id": sg.id, "question": sg.question, "intent": sg.intent, "entities": sg.entities}
                for sg in result.sub_goals
            ],
        }
    if name == "retrieve" and isinstance(result, Evidence):
        return {
            "mode": result.retrieval_mode,
            "chunk_count": len(result.chunks),
            "source_files": sorted({chunk.source_file for chunk in result.chunks}),
            "chunks": [
                {
                    "source_file": chunk.source_file,
                    "section": chunk.section,
                    "dense_rank": chunk.dense_rank,
                    "bm25_rank": chunk.bm25_rank,
                    "fused_score": round(chunk.fused_score, 4),
                }
                for chunk in result.chunks
            ],
        }
    if name == "tools" and isinstance(result, Draft):
        return {"claims": len(result.claims)}
    if name == "review" and isinstance(result, Review):
        return {
            "verdict": result.verdict,
            "unsupported_claims": result.unsupported_claims,
            "ambiguity_flags": result.ambiguity_flags,
        }
    if name == "answer" and isinstance(result, AnswerAssembly):
        return {"sources": list(result.sources)}
    return {}

