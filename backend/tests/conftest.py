"""Shared test fixtures: install scriptable fakes by default."""

from __future__ import annotations

import pytest

from app.providers import openai as openai_providers
from tests.fakes.embeddings import FakeEmbeddingProvider
from tests.fakes.llm import FakeLLMClient


@pytest.fixture(autouse=True)
def install_fake_providers(request: pytest.FixtureRequest, monkeypatch: pytest.MonkeyPatch):
    """Install fakes so no test hits a real provider unless it opts out.

    Opt out with ``@pytest.mark.real_providers`` (used by the provider adapter
    tests that construct clients directly with a mocked transport).
    """
    if request.node.get_closest_marker("real_providers"):
        yield
        return
    monkeypatch.setattr(openai_providers, "build_llm_client", lambda _s: FakeLLMClient())
    monkeypatch.setattr(
        openai_providers, "build_embedding_provider", lambda _s: FakeEmbeddingProvider()
    )
    yield
