"""Service layer: run the pipeline and map errors for POST /ask."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from app.agent.answer import Answerer
from app.agent.events import StageEvent
from app.agent.pipeline import Pipeline
from app.agent.plan import Planner
from app.agent.review import Reviewer
from app.agent.tool_runner import ToolRunner
from app.agent.tools import build_tool_registry
from app.agent.tools.base import ToolRegistry
from app.agent.usage import TokenTrackingLLMClient
from app.core.config import Settings
from app.core.errors import (
    AppError,
    ConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)
from app.providers import openai as openai_providers
from app.providers.protocols import LLMClient
from app.providers.protocols import ProviderError as ProviderProtocolError
from app.retrieval.index_manager import IndexManager
from app.schemas.domain import AskResponse

logger = logging.getLogger(__name__)


def translate_provider_error(exc: ProviderProtocolError) -> AppError:
    """Map a provider error to the corresponding core AppError (for HTTP mapping)."""
    if exc.code == "configuration_error":
        return ConfigurationError(exc.message)
    if exc.code == "rate_limited":
        return RateLimitError(exc.message)
    if exc.code == "provider_timeout":
        return ProviderTimeoutError(exc.message)
    return ProviderError(exc.message)


class AskService:
    """Runs the five-stage pipeline for a question and returns the response."""

    def __init__(self, settings: Settings, index_manager: IndexManager) -> None:
        self._settings = settings
        self._index_manager = index_manager
        # Shared across requests: the underlying client carries the concurrency
        # semaphore and the cached structured-output probe, and the registry is a
        # read-only allowlist over the immutable chunk list.
        self._llm_client: LLMClient | None = None
        self._tool_registry: ToolRegistry | None = None
        # Last completed run's stage events (informational; per-run events are
        # streamed/returned through the pipeline, never through this property).
        self._last_events: list[StageEvent] = []

    @property
    def events(self) -> list[StageEvent]:
        return list(self._last_events)

    async def ask(self, question: str, trace_id: str | None) -> AskResponse:
        return await self._run(question, trace_id, on_event=None)

    async def ask_streaming(
        self,
        question: str,
        trace_id: str | None,
        on_event: Callable[[StageEvent], Awaitable[None]],
    ) -> AskResponse:
        return await self._run(question, trace_id, on_event=on_event)

    async def _run(
        self,
        question: str,
        trace_id: str | None,
        on_event: Callable[[StageEvent], Awaitable[None]] | None,
    ) -> AskResponse:
        await self._index_manager.await_ready(self._settings.index_ready_timeout_s)
        if self._settings.llm_provider != "fake" and not self._settings.llm_configured:
            raise ConfigurationError(
                "LLM is not configured. Set OPENAI_API_KEY, OPENAI_BASE_URL and OPENAI_MODEL."
            )

        # A fresh pipeline (and a fresh token tracker) per request keeps the
        # mutable per-run state — token usage, tool results and stage events —
        # isolated when /ask is hit concurrently. The LLM client, retriever and
        # tool registry are shared but read-only/thread-safe.
        pipeline = self._build_pipeline()
        start = time.perf_counter()
        try:
            response = await pipeline.run(question, trace_id=trace_id, on_event=on_event)
        except ProviderProtocolError as exc:
            raise translate_provider_error(exc) from exc
        self._last_events = pipeline.events
        latency_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "ask_completed",
            extra={
                "latency_ms": round(latency_ms, 1),
                "tokens_in": response.usage.tokens_in,
                "tokens_out": response.usage.tokens_out,
                "verdict": response.review.verdict,
                "tool_names": [record.tool for record in response.tool_calls],
                "retrieval_mode": response.retrieval_mode,
            },
        )
        return response

    def _get_llm_client(self) -> LLMClient:
        if self._llm_client is None:
            self._llm_client = openai_providers.build_llm_client(self._settings)
        return self._llm_client

    def _get_tool_registry(self) -> ToolRegistry:
        if self._tool_registry is None:
            self._tool_registry = build_tool_registry(
                self._index_manager.chunks, self._index_manager.glossary_entries
            )
        return self._tool_registry

    def _build_pipeline(self) -> Pipeline:
        retriever = self._index_manager.retriever
        if retriever is None:
            raise ConfigurationError("The corpus index is unavailable.")
        tracker = TokenTrackingLLMClient(self._get_llm_client())
        return Pipeline(
            Planner(tracker),
            retriever,
            ToolRunner(tracker, self._get_tool_registry()),
            Reviewer(tracker),
            Answerer(),
            usage=tracker,
            timeout_s=self._settings.request_timeout_s,
        )
