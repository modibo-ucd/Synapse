"""Deterministic, scriptable fake LLM client for tests.

Every call must be scripted first; unscripted calls raise. This keeps tests
strict: a forgotten script fails loudly instead of silently returning empty text.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.providers.protocols import LLMResult, Messages, ToolCall, ToolChatResult, ToolSpec


class FakeLLMClient:
    """Scriptable LLMClient. Raises ``AssertionError`` on any unscripted call."""

    def __init__(self) -> None:
        self._text_scripts: list[Any] = []
        self._structured_scripts: list[Any] = []
        self._tool_scripts: list[Any] = []
        # Records every call as (method, messages) so tests can assert the prompt
        # defense (delimited, untrusted-marked blocks) without inspecting internals.
        self.calls: list[tuple[str, Messages]] = []

    def script_text(self, result: str | LLMResult[str] | Exception) -> None:
        self._text_scripts.append(
            result if not isinstance(result, str) else LLMResult(result, result)
        )

    def script_structured(self, result: BaseModel | LLMResult[Any] | Exception) -> None:
        self._structured_scripts.append(result)

    def script_tools(
        self, result: ToolChatResult | list[ToolCall] | Exception
    ) -> None:
        self._tool_scripts.append(
            result if not isinstance(result, list) else ToolChatResult(None, result)
        )

    async def generate_text(self, messages: Messages) -> LLMResult[str]:
        self.calls.append(("generate_text", messages))
        return self._pop(self._text_scripts, "generate_text")

    async def generate_structured(
        self, messages: Messages, schema: type[BaseModel]
    ) -> LLMResult[Any]:
        self.calls.append(("generate_structured", messages))
        item = self._pop(self._structured_scripts, "generate_structured")
        if isinstance(item, BaseModel):
            return LLMResult(content=item.model_dump_json(), parsed=item)
        return item

    async def chat_with_tools(
        self, messages: Messages, tools: list[ToolSpec]
    ) -> ToolChatResult:
        self.calls.append(("chat_with_tools", messages))
        return self._pop(self._tool_scripts, "chat_with_tools")

    @staticmethod
    def _pop(scripts: list[Any], name: str) -> Any:
        if not scripts:
            raise AssertionError(f"FakeLLMClient.{name} called without a scripted result")
        item = scripts.pop(0)
        if isinstance(item, Exception):
            raise item
        return item
