"""Tests for Settings: quote stripping, defaults and llm_configured."""

from __future__ import annotations

from app.core.config import Settings

OPENAI_NAMES = ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")


def _clear_openai_env(monkeypatch) -> None:
    for name in OPENAI_NAMES:
        monkeypatch.delenv(name, raising=False)


def test_string_fields_strip_whitespace_and_quotes(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", '  "sk-quoted"  ')
    monkeypatch.setenv("OPENAI_MODEL", "'gpt-5.6-terra'")
    settings = Settings(_env_file=None)
    assert settings.openai_api_key == "sk-quoted"
    assert settings.openai_model == "gpt-5.6-terra"


def test_unquoted_string_passes_through(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_MODEL", "gpt-5.6-terra")
    settings = Settings(_env_file=None)
    assert settings.openai_model == "gpt-5.6-terra"


def test_non_string_fields_coerce_after_stripping(monkeypatch) -> None:
    monkeypatch.setenv("MAX_SUB_GOALS", '"5"')
    monkeypatch.setenv("SEMANTIC_CACHE_ENABLED", "true")
    settings = Settings(_env_file=None)
    assert settings.max_sub_goals == 5
    assert settings.semantic_cache_enabled is True


def test_llm_configured_false_without_env(monkeypatch) -> None:
    _clear_openai_env(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.llm_configured is False


def test_llm_configured_true_with_env(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "key")
    monkeypatch.setenv("OPENAI_BASE_URL", "https://example.com")
    monkeypatch.setenv("OPENAI_MODEL", "m")
    settings = Settings(_env_file=None)
    assert settings.llm_configured is True


def test_defaults(monkeypatch) -> None:
    _clear_openai_env(monkeypatch)
    settings = Settings(_env_file=None)
    assert settings.openai_embedding_model == "text-embedding-3-small"
    assert settings.llm_provider == "openai"
    assert settings.max_sub_goals == 5
    assert settings.max_tool_calls == 4
    assert settings.request_timeout_s == 90
    assert settings.rate_limit_per_min == 0
    assert settings.semantic_cache_enabled is False
    assert settings.log_level == "INFO"
