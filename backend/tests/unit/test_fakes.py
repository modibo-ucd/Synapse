"""Tests for the scriptable fake providers."""

from __future__ import annotations

import pytest
from pydantic import BaseModel

from app.providers.protocols import ToolCall
from tests.fakes.embeddings import FakeEmbeddingProvider
from tests.fakes.llm import FakeLLMClient


class Plan(BaseModel):
    complexity: str
    in_scope: bool


async def test_fake_llm_raises_on_unscripted() -> None:
    fake = FakeLLMClient()
    with pytest.raises(AssertionError):
        await fake.generate_text([{"role": "user", "content": "hi"}])


async def test_fake_llm_script_text() -> None:
    fake = FakeLLMClient()
    fake.script_text("pong")
    result = await fake.generate_text([{"role": "user", "content": "hi"}])
    assert result.parsed == "pong"
    assert result.content == "pong"
    with pytest.raises(AssertionError):
        await fake.generate_text([])


async def test_fake_llm_script_structured_model() -> None:
    fake = FakeLLMClient()
    fake.script_structured(Plan(complexity="simple", in_scope=True))
    result = await fake.generate_structured([], Plan)
    assert result.parsed == Plan(complexity="simple", in_scope=True)


async def test_fake_llm_script_tools() -> None:
    fake = FakeLLMClient()
    fake.script_tools([ToolCall(name="t", arguments={"a": 1})])
    result = await fake.chat_with_tools([], [])
    assert result.tool_calls == [ToolCall(name="t", arguments={"a": 1})]


async def test_fake_llm_script_error() -> None:
    fake = FakeLLMClient()
    fake.script_text(ValueError("boom"))
    with pytest.raises(ValueError):
        await fake.generate_text([])


async def test_fake_embedding_deterministic_hash() -> None:
    provider = FakeEmbeddingProvider(dimension=8)
    first = await provider.embed_batch(["warfarin"])
    second = await provider.embed_batch(["warfarin"])
    other = await provider.embed_batch(["apixaban"])
    assert first == second
    assert first != other
    assert len(first[0]) == 8


async def test_fake_embedding_scripted() -> None:
    provider = FakeEmbeddingProvider(dimension=2)
    provider.script([[1.0, 2.0]])
    assert await provider.embed_batch(["a"]) == [[1.0, 2.0]]
