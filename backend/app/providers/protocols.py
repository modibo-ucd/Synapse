"""Provider-agnostic protocols and result types."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Generic, Protocol, TypeVar

from pydantic import BaseModel

# OpenAI-style chat message list (role/content/tool_call_id/...). Provider-agnostic.
Messages = list[dict[str, Any]]

T = TypeVar("T")
SchemaT = TypeVar("SchemaT", bound=BaseModel)


class ProviderError(Exception):
    """Error raised by LLM/embedding providers.

    ``retryable`` drives the capped exponential-backoff retry loop; ``code`` is
    the stable code used in the API's single error JSON shape.
    """

    def __init__(self, message: str, *, retryable: bool, code: str) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.code = code


@dataclass(frozen=True)
class ToolSpec:
    """A tool the model may invoke (its arguments are a JSON Schema)."""

    name: str
    description: str
    parameters: dict[str, Any]


@dataclass(frozen=True)
class ToolCall:
    """A tool call requested by the model."""

    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResult(Generic[T]):
    """A completed LLM response with typed parsed content, usage and latency."""

    content: str
    parsed: T
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0


@dataclass
class ToolChatResult:
    """Result of a tool-calling chat completion."""

    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0


class LLMClient(Protocol):
    """Structured / text / tool-calling LLM interface."""

    async def generate_structured(
        self, messages: Messages, schema: type[SchemaT]
    ) -> LLMResult[SchemaT]: ...

    async def generate_text(self, messages: Messages) -> LLMResult[str]: ...

    async def chat_with_tools(
        self, messages: Messages, tools: list[ToolSpec]
    ) -> ToolChatResult: ...


class EmbeddingProvider(Protocol):
    """Text-embedding interface."""

    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
