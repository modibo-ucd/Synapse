"""Concurrency: concurrent /ask requests keep per-run state isolated and never
corrupt the shared in-memory index."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.core.config import Settings
from app.providers import openai as openai_providers
from app.providers.protocols import LLMResult, Messages, SchemaT, ToolChatResult, ToolSpec
from app.retrieval.index_manager import IndexManager
from app.schemas.domain import Claim, Draft, Plan, Review, SubGoal
from app.services.ask_service import AskService
from tests.fakes.embeddings import FakeEmbeddingProvider

PLAN_IN, TOOLS_IN, DRAFT_IN, REVIEW_IN = 5, 1, 2, 1
TOTAL_IN = PLAN_IN + TOOLS_IN + DRAFT_IN + REVIEW_IN


class _FixedFake:
    """Concurrent-safe fake: fixed results keyed by method, with no script queue.

    A shared token tracker would accumulate across requests (so a later response
    would report more than ``TOTAL_IN`` tokens); a per-request tracker always
    reports exactly ``TOTAL_IN``.
    """

    def __init__(self, chunk_id: str) -> None:
        self._chunk_id = chunk_id
        self.calls: list[str] = []

    async def generate_structured(self, messages: Messages, schema: type[SchemaT]) -> LLMResult:
        self.calls.append("generate_structured")
        if schema is Plan:
            parsed = Plan(
                complexity="simple",
                in_scope=True,
                sub_goals=[
                    SubGoal(id="sg1", question="warfarin contraindications", entities=["warfarin"])
                ],
            )
            tokens = PLAN_IN
        elif schema is Draft:
            parsed = Draft(
                claims=[
                    Claim(
                        text="warfarin is contraindicated in pregnancy",
                        evidence_ids=[self._chunk_id],
                    )
                ]
            )
            tokens = DRAFT_IN
        elif schema is Review:
            parsed = Review(verdict="pass")
            tokens = REVIEW_IN
        else:  # pragma: no cover - strict fakes raise on unscripted calls
            raise AssertionError(f"unexpected schema {schema}")
        return LLMResult(content="", parsed=parsed, tokens_in=tokens, tokens_out=1)

    async def chat_with_tools(self, messages: Messages, tools: list[ToolSpec]) -> ToolChatResult:
        self.calls.append("chat_with_tools")
        return ToolChatResult(None, [], tokens_in=TOOLS_IN, tokens_out=1)

    async def generate_text(self, messages: Messages) -> LLMResult[str]:
        raise AssertionError("generate_text must not be called by the pipeline")


def _corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "dailymed-warfarin.md").write_text(
        "# Warfarin (DailyMed label)\n\n"
        "## 4 CONTRAINDICATIONS\n\n"
        "warfarin is contraindicated in pregnancy.\n",
        encoding="utf-8",
    )
    return corpus


def _make_service(tmp_path: Path) -> tuple[AskService, IndexManager]:
    corpus = _corpus(tmp_path)
    settings = Settings(
        _env_file=None,
        corpus_dir=str(corpus),
        cache_dir=str(tmp_path / "cache"),
        llm_provider="fake",
    )
    manager = IndexManager(settings, FakeEmbeddingProvider())
    return AskService(settings, manager), manager


async def _ready(manager: IndexManager) -> None:
    manager.start()
    await manager.await_ready(30.0)


async def test_sequential_asks_isolate_token_usage(tmp_path, monkeypatch) -> None:
    service, manager = _make_service(tmp_path)
    await _ready(manager)
    fake = _FixedFake(manager.chunks[0].chunk_id)
    monkeypatch.setattr(openai_providers, "build_llm_client", lambda _s: fake)

    for _ in range(3):
        response = await service.ask("warfarin contraindications", None)
        assert response.usage.tokens_in == TOTAL_IN
        assert response.sources == ["dailymed-warfarin.md"]
        assert response.disclaimer in response.answer

    # Three requests x (plan + draft + review structured, tools chat).
    assert fake.calls.count("generate_structured") == 9
    assert fake.calls.count("chat_with_tools") == 3


async def test_ten_parallel_asks_do_not_corrupt_state(tmp_path, monkeypatch) -> None:
    service, manager = _make_service(tmp_path)
    await _ready(manager)
    fake = _FixedFake(manager.chunks[0].chunk_id)
    monkeypatch.setattr(openai_providers, "build_llm_client", lambda _s: fake)

    responses = await asyncio.gather(
        *(service.ask("warfarin contraindications", None) for _ in range(10))
    )

    assert len(responses) == 10
    for response in responses:
        assert response.usage.tokens_in == TOTAL_IN
        assert response.sources == ["dailymed-warfarin.md"]
        assert response.disclaimer in response.answer

    # The shared index survives the burst untouched and remains queryable.
    assert manager.retriever is not None
    assert manager.status in {"ready", "degraded"}
    assert manager.chunks
