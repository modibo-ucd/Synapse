"""Tests for the OpenAI provider adapters (mocked HTTP transport)."""

from __future__ import annotations

import json

import httpx2
import pytest
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.providers import openai as openai_providers
from app.providers.openai import OpenAIEmbeddingProvider, OpenAILLMClient
from app.providers.protocols import ProviderError, ToolCall, ToolSpec


class Plan(BaseModel):
    complexity: str
    in_scope: bool


async def _noop_backoff(attempt: int) -> None:
    return None


def _json_response(payload: dict, status_code: int = 200) -> httpx2.Response:
    return httpx2.Response(status_code, json=payload)


def _chat_payload(content: str | None = None, tool_calls: list | None = None) -> dict:
    if tool_calls is not None:
        message: dict = {"role": "assistant", "content": None, "tool_calls": tool_calls}
    else:
        message = {"role": "assistant", "content": content}
    return {
        "id": "cmpl-1",
        "object": "chat.completion",
        "model": "gpt-test",
        "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    }


def _embed_payload(vectors: list[list[float]]) -> dict:
    return {
        "object": "list",
        "model": "text-embedding-3-small",
        "data": [
            {"object": "embedding", "index": i, "embedding": v}
            for i, v in enumerate(vectors)
        ],
        "usage": {"prompt_tokens": 3, "total_tokens": 3},
    }


def _make_llm(handler, *, max_retries: int = 2) -> OpenAILLMClient:
    client = AsyncOpenAI(
        api_key="k",
        base_url="https://test/v1",
        http_client=httpx2.AsyncClient(
            transport=httpx2.MockTransport(handler), base_url="https://test/v1"
        ),
        max_retries=0,
        timeout=5.0,
    )
    return OpenAILLMClient(client=client, model="gpt-test", max_retries=max_retries)


def _make_embedding(handler, *, batch_size: int = 2) -> OpenAIEmbeddingProvider:
    client = AsyncOpenAI(
        api_key="k",
        base_url="https://test/v1",
        http_client=httpx2.AsyncClient(
            transport=httpx2.MockTransport(handler), base_url="https://test/v1"
        ),
        max_retries=0,
        timeout=5.0,
    )
    return OpenAIEmbeddingProvider(
        client=client, model="text-embedding-3-small", batch_size=batch_size
    )


async def test_generate_text() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return _json_response(_chat_payload(content="pong"))

    result = await _make_llm(handler).generate_text([{"role": "user", "content": "hi"}])
    assert result.parsed == "pong"
    assert result.tokens_in == 10
    assert result.tokens_out == 5
    assert result.latency_ms >= 0


async def test_generate_structured_success_uses_json_schema() -> None:
    formats: list = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        formats.append(json.loads(request.content).get("response_format"))
        return _json_response(_chat_payload(content='{"complexity": "simple", "in_scope": true}'))

    result = await _make_llm(handler).generate_structured(
        [{"role": "user", "content": "classify"}], Plan
    )
    assert result.parsed == Plan(complexity="simple", in_scope=True)
    assert [f["type"] for f in formats] == ["json_schema", "json_schema"]
    assert formats[0]["json_schema"]["name"] == "probe"
    assert formats[1]["json_schema"]["name"] == "Plan"


async def test_generate_structured_repair_retry() -> None:
    calls: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls.append(json.loads(request.content)["messages"][0]["content"])
        if len(calls) == 2:  # first actual call after the probe
            return _json_response(_chat_payload(content="not json"))
        return _json_response(_chat_payload(content='{"complexity": "simple", "in_scope": true}'))

    result = await _make_llm(handler).generate_structured(
        [{"role": "user", "content": "classify"}], Plan
    )
    assert result.parsed == Plan(complexity="simple", in_scope=True)
    assert len(calls) == 3  # probe + invalid + repair


async def test_generate_structured_repair_gives_up() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return _json_response(_chat_payload(content="not json"))

    llm = _make_llm(handler)
    with pytest.raises(ProviderError) as excinfo:
        await llm.generate_structured([{"role": "user", "content": "x"}], Plan)
    assert excinfo.value.code == "provider_error"
    assert excinfo.value.retryable is False


async def test_generate_structured_falls_back_to_json_object() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        rf = body.get("response_format")
        if rf and rf.get("type") == "json_schema":
            return _json_response(
                {"error": {"message": "unsupported", "type": "invalid_request_error"}},
                status_code=400,
            )
        return _json_response(_chat_payload(content='{"complexity": "simple", "in_scope": true}'))

    result = await _make_llm(handler).generate_structured(
        [{"role": "user", "content": "x"}], Plan
    )
    assert result.parsed == Plan(complexity="simple", in_scope=True)


async def test_chat_with_tools_parses_tool_calls() -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return _json_response(
            _chat_payload(
                tool_calls=[
                    {
                        "id": "call_1",
                        "type": "function",
                        "function": {"name": "get_weather", "arguments": '{"city": "Paris"}'},
                    }
                ]
            )
        )

    spec = ToolSpec(
        name="get_weather",
        description="weather",
        parameters={"type": "object", "properties": {"city": {"type": "string"}}},
    )
    result = await _make_llm(handler).chat_with_tools(
        [{"role": "user", "content": "weather?"}], [spec]
    )
    assert result.tool_calls == [ToolCall(name="get_weather", arguments={"city": "Paris"})]


@pytest.mark.parametrize(
    ("status_code", "error_code", "retryable"),
    [
        (401, "configuration_error", False),
        (403, "configuration_error", False),
        (429, "rate_limited", True),
        (502, "provider_error", True),
    ],
)
async def test_error_mapping(status_code, error_code, retryable) -> None:
    def handler(request: httpx2.Request) -> httpx2.Response:
        return _json_response({"error": {"message": "err", "type": "x"}}, status_code=status_code)

    with pytest.raises(ProviderError) as excinfo:
        await _make_llm(handler).generate_text([{"role": "user", "content": "hi"}])
    assert excinfo.value.code == error_code
    assert excinfo.value.retryable is retryable


async def test_retries_rate_limit_then_succeeds(monkeypatch) -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        if calls["n"] < 3:
            return _json_response(
                {"error": {"message": "slow down", "type": "x"}}, status_code=429
            )
        return _json_response(_chat_payload(content="pong"))

    monkeypatch.setattr(openai_providers, "_backoff", _noop_backoff)
    result = await _make_llm(handler, max_retries=2).generate_text(
        [{"role": "user", "content": "hi"}]
    )
    assert result.parsed == "pong"
    assert calls["n"] == 3


async def test_timeout_maps_to_provider_timeout(monkeypatch) -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        raise httpx2.ReadTimeout("timeout")

    monkeypatch.setattr(openai_providers, "_backoff", _noop_backoff)
    llm = _make_llm(handler, max_retries=1)
    with pytest.raises(ProviderError) as excinfo:
        await llm.generate_text([{"role": "user", "content": "hi"}])
    assert excinfo.value.code == "provider_timeout"
    assert excinfo.value.retryable is True
    assert calls["n"] == 2


async def test_no_retry_on_configuration_error() -> None:
    calls = {"n": 0}

    def handler(request: httpx2.Request) -> httpx2.Response:
        calls["n"] += 1
        return _json_response({"error": {"message": "bad key", "type": "x"}}, status_code=401)

    with pytest.raises(ProviderError):
        await _make_llm(handler, max_retries=2).generate_text(
            [{"role": "user", "content": "hi"}]
        )
    assert calls["n"] == 1


async def test_embed_batch_chunks_and_preserves_order() -> None:
    inputs: list[list[str]] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        body = json.loads(request.content)
        inputs.append(body["input"])
        n = len(body["input"])
        return _json_response(_embed_payload([[float(i)] for i in range(n)]))

    provider = _make_embedding(handler, batch_size=2)
    vectors = await provider.embed_batch(["a", "b", "c", "d", "e"])
    assert len(vectors) == 5
    assert inputs == [["a", "b"], ["c", "d"], ["e"]]


@pytest.mark.real_providers
def test_build_llm_client_fake_branch() -> None:
    from app.core.config import Settings
    from tests.fakes.llm import FakeLLMClient

    settings = Settings(_env_file=None, llm_provider="fake")
    assert isinstance(openai_providers.build_llm_client(settings), FakeLLMClient)


@pytest.mark.real_providers
def test_build_llm_client_openai_branch() -> None:
    from app.core.config import Settings

    settings = Settings(
        _env_file=None,
        llm_provider="openai",
        openai_api_key="k",
        openai_base_url="https://test/v1",
        openai_model="gpt-test",
    )
    assert isinstance(openai_providers.build_llm_client(settings), OpenAILLMClient)


@pytest.mark.real_providers
def test_build_embedding_provider_fake_branch() -> None:
    from app.core.config import Settings
    from tests.fakes.embeddings import FakeEmbeddingProvider

    settings = Settings(_env_file=None, llm_provider="fake")
    assert isinstance(openai_providers.build_embedding_provider(settings), FakeEmbeddingProvider)
