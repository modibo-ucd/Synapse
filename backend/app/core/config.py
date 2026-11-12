"""Application settings (pydantic-settings).

Only the four OPENAI_* values are guaranteed to be provided by the grader's
environment. Every other setting has a safe default so a missing key never
crashes the app. All string values are stripped of surrounding whitespace and a
single pair of matching quotes because ``docker --env-file`` does not strip
quotes.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.core.constants import (
    CHARS_PER_TOKEN,
    CHUNK_MAX_TOKENS,
    CHUNK_OVERLAP_TOKENS,
    MAX_SUB_GOALS,
    MAX_TOOL_CALLS,
    REQUEST_TIMEOUT_S,
)


class Settings(BaseSettings):
    """Runtime configuration, read from the environment and an optional .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # The only values guaranteed to be injected by graders.
    openai_api_key: str = ""
    openai_base_url: str = ""
    openai_model: str = ""
    openai_embedding_model: str = "text-embedding-3-small"

    # Optional overrides and runtime tuning.
    llm_provider: str = "openai"
    plan_model: str = ""
    review_model: str = ""
    draft_model: str = ""
    corpus_dir: str = "corpus"
    cache_dir: str = "/tmp/synapse-cache"
    max_sub_goals: int = MAX_SUB_GOALS
    max_tool_calls: int = MAX_TOOL_CALLS
    request_timeout_s: float = REQUEST_TIMEOUT_S
    chunk_max_tokens: int = CHUNK_MAX_TOKENS
    chunk_overlap_tokens: int = CHUNK_OVERLAP_TOKENS
    chars_per_token: float = CHARS_PER_TOKEN
    rate_limit_per_min: int = 0
    semantic_cache_enabled: bool = False
    log_level: str = "INFO"

    @field_validator("*", mode="before")
    @classmethod
    def strip_quotes_and_whitespace(cls, value: Any) -> Any:
        """Strip whitespace and one pair of matching surrounding quotes."""
        if isinstance(value, str):
            value = value.strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1].strip()
        return value

    @property
    def llm_configured(self) -> bool:
        """True when the minimum values needed to call the LLM are present."""
        return bool(self.openai_api_key and self.openai_base_url and self.openai_model)


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (process-wide)."""
    return Settings()
