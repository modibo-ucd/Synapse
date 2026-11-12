"""Integration tests for POST /ask/stream (SSE) over HTTP using fakes."""

from __future__ import annotations

import asyncio
import json
import threading
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers import openai as openai_providers
from app.providers.protocols import LLMResult, ToolChatResult
from app.retrieval.chunker import chunk_documents
from app.retrieval.loader import load_documents
from app.schemas.domain import Claim, Draft, Plan, Review, SubGoal
from tests.fakes.llm import FakeLLMClient


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


def _settings(tmp_path: Path, corpus: Path) -> Settings:
    return Settings(
        _env_file=None,
        corpus_dir=str(corpus),
        cache_dir=str(tmp_path / "cache"),
        llm_provider="fake",
    )


def _collect_sse(response) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    name = "message"
    for line in response.iter_lines():
        if line.startswith("event:"):
            name = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            events.append((name, json.loads(line.split(":", 1)[1].strip())))
    return events


def test_stream_emits_stages_then_result(monkeypatch, tmp_path) -> None:
    corpus = _corpus(tmp_path)
    chunk = chunk_documents(load_documents(corpus))[0]

    fake = FakeLLMClient()
    fake.script_structured(
        Plan(
            complexity="simple",
            in_scope=True,
            sub_goals=[
                SubGoal(
                    id="sg1",
                    question="warfarin contraindications",
                    entities=["warfarin"],
                )
            ],
        )
    )
    fake.script_tools(ToolChatResult(None, []))
    fake.script_structured(
        Draft(
            claims=[
                Claim(
                    text="warfarin is contraindicated in pregnancy",
                    evidence_ids=[chunk.chunk_id],
                )
            ]
        )
    )
    fake.script_structured(Review(verdict="pass"))
    monkeypatch.setattr(openai_providers, "build_llm_client", lambda _s: fake)

    app = create_app(_settings(tmp_path, corpus))
    with TestClient(app) as client:
        with client.stream(
            "POST", "/ask/stream", json={"question": "What are warfarin contraindications?"}
        ) as response:
            assert response.status_code == 200
            events = _collect_sse(response)

    stages = [data["stage"] for name, data in events if name == "stage"]
    assert stages == ["plan", "retrieve", "tools", "review", "answer"]
    assert all(data["status"] == "ok" for name, data in events if name == "stage")

    results = [data for name, data in events if name == "result"]
    assert len(results) == 1
    assert results[0]["sources"] == ["dailymed-warfarin.md"]

    plan = next(data for name, data in events if name == "stage" and data["stage"] == "plan")
    assert plan["details"]["sub_goals"]
    tools = next(
        data for name, data in events if name == "stage" and data["stage"] == "tools"
    )
    assert "tool_calls" in tools["details"]
    retrieve = next(
        data for name, data in events if name == "stage" and data["stage"] == "retrieve"
    )
    # Retrieve details are UI-safe: file names/sections/ranks, never raw passages.
    assert retrieve["details"]["source_files"] == ["dailymed-warfarin.md"]


class BlockingLLM:
    """Blocks forever on the first structured call to exercise disconnect cancellation."""

    def __init__(self) -> None:
        self.cancelled = threading.Event()

    async def generate_structured(self, messages, schema):
        try:
            await asyncio.sleep(3600)
        except asyncio.CancelledError:
            self.cancelled.set()
            raise
        return LLMResult(content="", parsed=schema())  # pragma: no cover - unreachable

    async def generate_text(self, messages):
        raise AssertionError("unexpected generate_text call")

    async def chat_with_tools(self, messages, tools):
        raise AssertionError("unexpected chat_with_tools call")


def test_stream_cancels_pipeline_on_disconnect(monkeypatch, tmp_path) -> None:
    blocking = BlockingLLM()
    monkeypatch.setattr(openai_providers, "build_llm_client", lambda _s: blocking)

    app = create_app(_settings(tmp_path, _corpus(tmp_path)))
    with TestClient(app) as client:
        with client.stream("POST", "/ask/stream", json={"question": "warfarin"}) as response:
            assert response.status_code == 200
            # Close the stream without reading; the pipeline task must be cancelled.

    assert blocking.cancelled.wait(timeout=5)
