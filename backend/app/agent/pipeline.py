"""The strict five-stage pipeline orchestrator."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from uuid import uuid4

from app.agent.answer import Answerer
from app.agent.events import PipelineContext, StageEvent
from app.agent.plan import Planner
from app.agent.review import Reviewer
from app.agent.tool_runner import ToolRunner
from app.agent.tools.base import ToolResult
from app.agent.usage import TokenTrackingLLMClient
from app.core.constants import REQUEST_TIMEOUT_S
from app.core.errors import PipelineTimeoutError
from app.retrieval.retriever import Retriever
from app.schemas.domain import (
    AnswerAssembly,
    AskResponse,
    Draft,
    Evidence,
    Plan,
    Review,
    ToolCallRecord,
    Usage,
)


class Pipeline:
    """Runs Plan -> Retrieve -> Tools -> Review -> Answer and builds the response."""

    def __init__(
        self,
        planner: Planner,
        retriever: Retriever,
        tool_runner: ToolRunner,
        reviewer: Reviewer,
        answerer: Answerer,
        *,
        usage: TokenTrackingLLMClient,
        timeout_s: float = REQUEST_TIMEOUT_S,
    ) -> None:
        self._planner = planner
        self._retriever = retriever
        self._tool_runner = tool_runner
        self._reviewer = reviewer
        self._answerer = answerer
        self._usage = usage
        self._timeout_s = timeout_s
        self._events: list[StageEvent] = []
        self._evidence: Evidence | None = None

    @property
    def events(self) -> list[StageEvent]:
        return list(self._events)

    @property
    def evidence(self) -> Evidence | None:
        return self._evidence

    async def run(
        self,
        question: str,
        *,
        trace_id: str | None = None,
        on_event: Callable[[StageEvent], Awaitable[None]] | None = None,
    ) -> AskResponse:
        trace_id = trace_id or uuid4().hex
        start = time.perf_counter()
        context = PipelineContext(on_event=on_event)
        try:
            plan, evidence, review, answer, tool_results = await asyncio.wait_for(
                self._run_stages(context, question), self._timeout_s
            )
        except TimeoutError as exc:
            raise PipelineTimeoutError(
                f"request timed out after {self._timeout_s:.0f}s"
            ) from exc
        self._events = context.events
        self._evidence = evidence
        latency_ms = (time.perf_counter() - start) * 1000

        return AskResponse(
            answer=answer.answer,
            sources=answer.sources,
            citations=answer.citations,
            disclaimer=answer.disclaimer,
            plan=plan,
            tool_calls=[
                ToolCallRecord(tool=result.tool, arguments=result.arguments, status=result.status)
                for result in tool_results
            ],
            review=review,
            retrieval_mode=evidence.retrieval_mode,
            trace_id=trace_id,
            usage=Usage(tokens_in=self._usage.tokens_in, tokens_out=self._usage.tokens_out),
            latency_ms=latency_ms,
            comparison=answer.comparison,
            widgets=answer.widgets,
        )

    async def _run_stages(
        self, context: PipelineContext, question: str
    ) -> tuple[Plan, Evidence, Review, AnswerAssembly, list[ToolResult]]:
        plan = await context.run_stage("plan", self._planner.run, question)
        if not plan.in_scope:
            await context.skip("retrieve", "out of scope")
            await context.skip("tools", "out of scope")
            await context.skip("review", "out of scope")
            await context.skip("answer", "out of scope")
            evidence = Evidence(chunks=[], retrieval_mode=self._retriever.retrieval_mode)
            return plan, evidence, Review(verdict="pass"), self._answerer.run_out_of_scope(), []

        evidence = await context.run_stage("retrieve", self._retriever.run, plan)
        draft: Draft = await context.run_stage(
            "tools",
            self._tool_runner.run,
            plan,
            evidence,
            details_fn=lambda _draft: {
                "tool_calls": [
                    {"tool": result.tool, "arguments": result.arguments, "status": result.status}
                    for result in self._tool_runner.last_tool_results
                ]
            },
        )
        tool_results = self._tool_runner.last_tool_results
        review = await context.run_stage(
            "review", self._reviewer.run, draft, evidence, tool_results, question
        )
        answer = await context.run_stage(
            "answer", self._answerer.run, draft, review, evidence, tool_results, question, plan
        )
        return plan, evidence, review, answer, tool_results
