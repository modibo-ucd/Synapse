"""LLM failure modes produce clean structured errors and never crash the process."""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.providers import openai as openai_providers
from app.providers.protocols import ProviderError
from tests.fakes.llm import FakeLLMClient


def _corpus(tmp_path: Path) -> Path:
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "dailymed-warfarin.md").write_text(
        "# Warfarin\n\n## 4 CONTRAINDICATIONS\n\nwarfarin is contraindicated in pregnancy.\n",
        encoding="utf-8",
    )
    return corpus


def _settings(tmp_path: Path, **overrides) -> Settings:
    kwargs: dict = {
        "_env_file": None,
        "corpus_dir": str(_corpus(tmp_path)),
        "cache_dir": str(tmp_path / "cache"),
        "llm_provider": "fake",
    }
    kwargs.update(overrides)
    return Settings(**kwargs)


def _raising_fake(code: str) -> FakeLLMClient:
    fake = FakeLLMClient()
    fake.script_structured(ProviderError("upstream failed", retryable=False, code=code))
    return fake


@pytest.mark.parametrize(
    ("code", "status"),
    [
        ("configuration_error", 503),
        ("rate_limited", 429),
        ("provider_timeout", 504),
        ("provider_error", 502),
    ],
)
def test_provider_failures_map_to_clean_errors(tmp_path, monkeypatch, code, status) -> None:
    monkeypatch.setattr(
        openai_providers, "build_llm_client", lambda _s: _raising_fake(code)
    )
    app = create_app(_settings(tmp_path))

    with TestClient(app) as client:
        resp = client.post("/ask", json={"question": "warfarin contraindications"})

    assert resp.status_code == status
    body = resp.json()
    assert set(body) == {"error"}
    assert body["error"]["code"] == code
    assert body["error"]["request_id"] is not None


def test_unreachable_base_url_keeps_health_up_and_errors_cleanly(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        openai_providers, "build_llm_client", lambda _s: _raising_fake("provider_error")
    )
    settings = _settings(
        tmp_path,
        llm_provider="openai",
        openai_api_key="k",
        openai_base_url="http://unreachable.invalid/v1",
        openai_model="m",
    )
    app = create_app(settings)

    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        resp = client.post("/ask", json={"question": "warfarin contraindications"})

    assert resp.status_code == 502
    assert resp.json()["error"]["code"] == "provider_error"
