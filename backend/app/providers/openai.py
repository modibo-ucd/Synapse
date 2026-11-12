"""OpenAI-compatible LLM and embedding providers built on AsyncOpenAI."""

from __future__ import annotations

import asyncio
import json
import random
from collections.abc import Awaitable, Callable
from typing import Any, TypeVar, cast

from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    PermissionDeniedError,
    RateLimitError,
)
from pydantic import BaseModel, ValidationError

from app.core.config import Settings
from app.providers.protocols import (
    EmbeddingProvider,
    LLMClient,
    LLMResult,
    Messages,
    ProviderError,
    SchemaT,
    ToolCall,
    ToolChatResult,
    ToolSpec,
)

MAX_RETRIES = 2
BACKOFF_BASE_S = 0.5
BACKOFF_MAX_S = 8.0
DEFAULT_MAX_CONCURRENCY = 4
EMBEDDING_BATCH_SIZE = 100

T = TypeVar("T")


def create_async_openai(settings: Settings) -> AsyncOpenAI:
    """Build an AsyncOpenAI client from settings (no SDK retries: we retry)."""
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url,
        timeout=settings.request_timeout_s,
        max_retries=0,
    )


def _map_openai_error(exc: Exception) -> ProviderError:
    if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
        return ProviderError(
            "LLM provider rejected the credentials or request (401/403).",
            retryable=False,
            code="configuration_error",
        )
    if isinstance(exc, RateLimitError):
        return ProviderError(
            "LLM provider rate limit reached.", retryable=True, code="rate_limited"
        )
    if isinstance(exc, APITimeoutError):
        return ProviderError(
            "LLM provider timed out.", retryable=True, code="provider_timeout"
        )
    if isinstance(exc, APIConnectionError):
        return ProviderError(
            "LLM provider connection error.", retryable=True, code="provider_error"
        )
    if isinstance(exc, APIStatusError):
        return ProviderError(
            f"LLM provider error (HTTP {exc.status_code}).",
            retryable=exc.status_code >= 500,
            code="provider_error",
        )
    return ProviderError(
        f"LLM provider unexpected error: {type(exc).__name__}.",
        retryable=False,
        code="provider_error",
    )


async def _backoff(attempt: int) -> None:
    delay = min(BACKOFF_MAX_S, BACKOFF_BASE_S * (2**attempt))
    await asyncio.sleep(delay + random.uniform(0.0, delay * 0.5))


async def _request_with_retry(
    semaphore: asyncio.Semaphore,
    call: Callable[..., Awaitable[T]],
    max_retries: int,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> T:
    """Run one provider call with a concurrency cap and capped backoff retries."""
    for attempt in range(max_retries + 1):
        try:
            async with semaphore:
                return await call(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - map all vendor errors centrally
            error = _map_openai_error(exc)
            if error.retryable and attempt < max_retries:
                await _backoff(attempt)
                continue
            raise error from exc
    raise AssertionError("unreachable")


class OpenAILLMClient:
    """LLMClient backed by an OpenAI-compatible chat completions endpoint."""

    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
        max_retries: int = MAX_RETRIES,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
    ) -> None:
        self._client = client
        self._model = model
        self._max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._structured_mode: str | None = None

    async def generate_text(self, messages: Messages) -> LLMResult[str]:
        start = asyncio.get_event_loop().time()
        content, _calls, tokens_in, tokens_out = await self._request(self._call_chat, messages)
        return LLMResult(
            content=content or "",
            parsed=content or "",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=self._elapsed_ms(start),
        )

    async def generate_structured(
        self, messages: Messages, schema: type[SchemaT]
    ) -> LLMResult[SchemaT]:
        start = asyncio.get_event_loop().time()
        mode = await self._ensure_structured_mode()
        if mode == "json_object":
            messages = [
                *messages,
                {"role": "system", "content": "Respond with only a JSON object."},
            ]
        for attempt in range(2):  # one repair retry on invalid JSON/schema
            try:
                content, _calls, tokens_in, tokens_out = await self._request(
                    self._call_chat,
                    messages,
                    response_format=self._structured_format(schema, mode),
                )
                parsed = schema.model_validate_json(content or "{}")
                return LLMResult(
                    content=content or "",
                    parsed=parsed,
                    tokens_in=tokens_in,
                    tokens_out=tokens_out,
                    latency_ms=self._elapsed_ms(start),
                )
            except (json.JSONDecodeError, ValidationError) as exc:
                if attempt == 0:
                    messages = [
                        *messages,
                        {"role": "user", "content": self._repair(exc, schema)},
                    ]
                    continue
                raise ProviderError(
                    "Structured output could not be validated after a repair attempt.",
                    retryable=False,
                    code="provider_error",
                ) from exc
        raise AssertionError("unreachable")

    async def chat_with_tools(
        self, messages: Messages, tools: list[ToolSpec]
    ) -> ToolChatResult:
        start = asyncio.get_event_loop().time()
        content, calls, tokens_in, tokens_out = await self._request(
            self._call_chat, messages, tools=tools
        )
        return ToolChatResult(
            content=content,
            tool_calls=calls,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=self._elapsed_ms(start),
        )

    async def _call_chat(
        self,
        messages: Messages,
        *,
        response_format: dict[str, Any] | None = None,
        tools: list[ToolSpec] | None = None,
    ) -> tuple[str | None, list[ToolCall], int, int]:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "temperature": 0,
        }
        if response_format is not None:
            kwargs["response_format"] = response_format
        if tools is not None:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t.name,
                        "description": t.description,
                        "parameters": t.parameters,
                    },
                }
                for t in tools
            ]
            kwargs["tool_choice"] = "auto"
        resp = await self._client.chat.completions.create(**kwargs)
        message = resp.choices[0].message
        usage = resp.usage
        tokens_in = usage.prompt_tokens if usage else 0
        tokens_out = usage.completion_tokens if usage else 0
        calls = [
            ToolCall(
                name=c.function.name, arguments=self._parse_args(c.function.arguments)
            )
            for c in (message.tool_calls or [])
        ]
        return message.content, calls, tokens_in, tokens_out

    @staticmethod
    def _parse_args(raw: str | None) -> dict[str, Any]:
        if not raw:
            return {}
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return {}
        return parsed if isinstance(parsed, dict) else {}

    async def _ensure_structured_mode(self) -> str:
        """Probe json_schema support once and cache the result."""
        if self._structured_mode is not None:
            return self._structured_mode
        probe_format = {
            "type": "json_schema",
            "json_schema": {
                "name": "probe",
                "schema": {
                    "type": "object",
                    "properties": {"ok": {"type": "boolean"}},
                    "required": ["ok"],
                },
            },
        }
        try:
            await self._request(
                self._call_chat,
                [{"role": "user", "content": 'Reply with {"ok": true}'}],
                response_format=probe_format,
            )
            self._structured_mode = "json_schema"
        except ProviderError as exc:
            if exc.code == "provider_error" and not exc.retryable:
                self._structured_mode = "json_object"
            else:
                raise
        return self._structured_mode

    @staticmethod
    def _structured_format(schema: type[BaseModel], mode: str) -> dict[str, Any]:
        if mode == "json_schema":
            return {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "schema": schema.model_json_schema(),
                },
            }
        return {"type": "json_object"}

    @staticmethod
    def _repair(exc: Exception, schema: type[BaseModel]) -> str:
        return (
            "Your previous response was not valid JSON matching the required schema. "
            f"Error: {exc}. Respond again with only a JSON object matching this schema: "
            f"{json.dumps(schema.model_json_schema())}"
        )

    async def _request(
        self, call: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        return await _request_with_retry(
            self._semaphore, call, self._max_retries, args, kwargs
        )

    @staticmethod
    def _elapsed_ms(start: float) -> float:
        return (asyncio.get_event_loop().time() - start) * 1000


class OpenAIEmbeddingProvider:
    """EmbeddingProvider backed by an OpenAI-compatible embeddings endpoint."""

    def __init__(
        self,
        *,
        client: AsyncOpenAI,
        model: str,
        max_retries: int = MAX_RETRIES,
        max_concurrency: int = DEFAULT_MAX_CONCURRENCY,
        batch_size: int = EMBEDDING_BATCH_SIZE,
    ) -> None:
        self._client = client
        self._model = model
        self._max_retries = max_retries
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._batch_size = batch_size

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        chunks = [
            texts[i : i + self._batch_size] for i in range(0, len(texts), self._batch_size)
        ]
        results = await asyncio.gather(
            *(self._request(self._call_embed, chunk) for chunk in chunks)
        )
        return [vector for chunk_result in results for vector in chunk_result]

    async def _call_embed(self, texts: list[str]) -> list[list[float]]:
        resp = await self._client.embeddings.create(model=self._model, input=texts)
        return [item.embedding for item in resp.data]

    async def _request(
        self, call: Callable[..., Awaitable[T]], *args: Any, **kwargs: Any
    ) -> T:
        return await _request_with_retry(
            self._semaphore, call, self._max_retries, args, kwargs
        )


def build_llm_client(settings: Settings) -> LLMClient:
    """Build the LLM client; ``LLM_PROVIDER=fake`` returns the scriptable fake."""
    if settings.llm_provider == "fake":
        from tests.fakes.llm import FakeLLMClient

        return cast(LLMClient, FakeLLMClient())
    return OpenAILLMClient(client=create_async_openai(settings), model=settings.openai_model)


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    """Build the embedding provider; ``LLM_PROVIDER=fake`` returns the fake."""
    if settings.llm_provider == "fake":
        from tests.fakes.embeddings import FakeEmbeddingProvider

        return cast(EmbeddingProvider, FakeEmbeddingProvider())
    return OpenAIEmbeddingProvider(
        client=create_async_openai(settings), model=settings.openai_embedding_model
    )
