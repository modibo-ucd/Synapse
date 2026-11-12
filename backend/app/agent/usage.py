"""Token-usage tracking wrapper around an LLMClient."""

from __future__ import annotations

from app.providers.protocols import (
    LLMClient,
    LLMResult,
    Messages,
    SchemaT,
    ToolChatResult,
    ToolSpec,
)


class TokenTrackingLLMClient:
    """Wraps an LLMClient and accumulates token usage across all calls."""

    def __init__(self, inner: LLMClient) -> None:
        self._inner = inner
        self.tokens_in = 0
        self.tokens_out = 0

    async def generate_structured(
        self, messages: Messages, schema: type[SchemaT]
    ) -> LLMResult[SchemaT]:
        result = await self._inner.generate_structured(messages, schema)
        self._record(result.tokens_in, result.tokens_out)
        return result

    async def generate_text(self, messages: Messages) -> LLMResult[str]:
        result = await self._inner.generate_text(messages)
        self._record(result.tokens_in, result.tokens_out)
        return result

    async def chat_with_tools(
        self, messages: Messages, tools: list[ToolSpec]
    ) -> ToolChatResult:
        result = await self._inner.chat_with_tools(messages, tools)
        self._record(result.tokens_in, result.tokens_out)
        return result

    def _record(self, tokens_in: int, tokens_out: int) -> None:
        self.tokens_in += tokens_in
        self.tokens_out += tokens_out
