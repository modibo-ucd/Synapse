"""Contract tests for the additive retrieval/trace fields on POST /ask."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import BaseModel, ConfigDict

from app.core.config import Settings
from app.main import create_app
from app.providers import openai as openai_providers
from app.providers.protocols import ToolChatResult
from app.retrieval.chunker import chunk_documents
from app.retrieval.loader import load_documents
from app.schemas.domain import AskResponse, Claim, Draft, Plan, Review, SubGoal
from tests.fakes.llm import FakeLLMClient


class _OldAskResponse(BaseModel):
    """The pre-Phase-A response shape; tolerates the new optional fields."""

    model_config = ConfigDict(extra="ignore")

    answer: str
    sources: list[str]
    citations: list[object]
    disclaimer: str
    plan: object
    tool_calls: list[object]
    review: object
    retrieval_mode: str
    trace_id: str
    usage: object
    latency_ms: float
    comparison: object | None = None
    widgets: object | None = None


def _corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "dailymed-warfarin.md").write_text(
        "# Warfarin (DailyMed label)\n\n## 4 CONTRAINDICATIONS\n\n"
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


def _scripted_fake(chunk_id: str) -> FakeLLMClient:
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
                    evidence_ids=[chunk_id],
                )
            ]
        )
    )
    fake.script_structured(Review(verdict="pass"))
    return fake


def test_ask_response_validates_against_old_and_new_model(monkeypatch, tmp_path) -> None:
    corpus = _corpus(tmp_path)
    chunk = chunk_documents(load_documents(corpus))[0]
    monkeypatch.setattr(
        openai_providers, "build_llm_client", lambda _s: _scripted_fake(chunk.chunk_id)
    )
    app = create_app(_settings(tmp_path, corpus))

    with TestClient(app) as client:
        resp = client.post("/ask", json={"question": "What are warfarin contraindications?"})

    assert resp.status_code == 200
    body = resp.json()

    # Old fields are intact and validate against the old model (new fields ignored).
    old = _OldAskResponse.model_validate(body)
    assert old.answer == body["answer"]
    assert old.sources == ["dailymed-warfarin.md"]
    assert old.retrieval_mode in {"hybrid", "bm25_only"}

    # The response also validates against the current (new) model.
    response = AskResponse.model_validate(body)
    assert response.retrieval is not None
    assert response.trace is not None

    # Retrieval info carries the cited chunk first and is capped at 12.
    retrieval = body["retrieval"]
    assert retrieval["mode"] in {"hybrid", "bm25_only"}
    assert retrieval["returned"] >= 1
    assert retrieval["candidates"] >= retrieval["returned"]
    assert len(retrieval["chunks"]) <= 12
    cited = [info for info in retrieval["chunks"] if info["chunk_id"] == chunk.chunk_id]
    assert cited and cited[0]["cited"] is True

    # Trace mirrors the five stages in order with UI-safe statuses.
    trace = body["trace"]
    assert [event["stage"] for event in trace] == ["plan", "retrieve", "tools", "review", "answer"]
    assert all(event["status"] in {"done", "skipped"} for event in trace)
