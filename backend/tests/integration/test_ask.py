"""Integration tests for POST /ask over HTTP using fakes."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers import openai as openai_providers
from app.providers.protocols import ToolChatResult
from app.retrieval.chunker import chunk_documents
from app.retrieval.loader import load_documents
from app.schemas.domain import Claim, Draft, Plan, Review, SubGoal
from tests.fakes.llm import FakeLLMClient

OPENAI_NAMES = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")


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


def test_ask_returns_200_with_valid_schema(monkeypatch, tmp_path) -> None:
    corpus = _corpus(tmp_path)
    chunk = chunk_documents(load_documents(corpus))[0]

    fake = FakeLLMClient()
    fake.script_structured(
        Plan(
            complexity="simple",
            in_scope=True,
            sub_goals=[
                SubGoal(id="sg1", question="warfarin contraindications", entities=["warfarin"])
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

    settings = Settings(
        _env_file=None,
        corpus_dir=str(corpus),
        cache_dir=str(tmp_path / "cache"),
        llm_provider="fake",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        resp = client.post("/ask", json={"question": "What are warfarin contraindications?"})

    assert resp.status_code == 200
    body = resp.json()
    assert set(body) == {
        "answer", "sources", "citations", "disclaimer", "plan", "tool_calls",
        "review", "retrieval_mode", "trace_id", "usage", "latency_ms", "comparison",
    }
    assert body["disclaimer"] and body["disclaimer"] in body["answer"]
    assert "dailymed-warfarin.md" in body["answer"]
    assert body["sources"] == ["dailymed-warfarin.md"]
    assert body["citations"] and body["citations"][0]["chunk_id"] == chunk.chunk_id
    assert body["citations"][0]["source_file"] == "dailymed-warfarin.md"

    events = app.state.ask_service.events
    assert [event.stage for event in events] == ["plan", "retrieve", "tools", "review", "answer"]
    assert all(event.status == "ok" for event in events)


def test_ask_validation_errors_are_422(tmp_path) -> None:
    corpus = _corpus(tmp_path)
    settings = Settings(
        _env_file=None,
        corpus_dir=str(corpus),
        cache_dir=str(tmp_path / "cache"),
        llm_provider="fake",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.post("/ask", json={}).status_code == 422
        assert client.post("/ask", json={"question": "   "}).status_code == 422
        assert client.post("/ask", json={"question": "x" * 2001}).status_code == 422


def test_ask_without_api_key_returns_503(monkeypatch, tmp_path) -> None:
    for name in OPENAI_NAMES:
        monkeypatch.delenv(name, raising=False)
    corpus = _corpus(tmp_path)
    settings = Settings(
        _env_file=None,
        corpus_dir=str(corpus),
        cache_dir=str(tmp_path / "cache"),
    )
    app = create_app(settings)
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        resp = client.post("/ask", json={"question": "warfarin contraindications"})

    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["code"] == "configuration_error"
