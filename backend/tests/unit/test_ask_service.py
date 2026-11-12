"""Tests for AskRequest validation and provider-error translation."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.errors import (
    ConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)
from app.providers.protocols import ProviderError as ProviderProtocolError
from app.schemas.domain import AskRequest
from app.services.ask_service import translate_provider_error


def test_ask_request_strips_and_tolerates_extra_fields() -> None:
    request = AskRequest.model_validate({"question": "  warfarin  ", "extra": 1})
    assert request.question == "warfarin"


def test_ask_request_rejects_empty_and_too_long() -> None:
    with pytest.raises(ValidationError):
        AskRequest.model_validate({"question": "   "})
    with pytest.raises(ValidationError):
        AskRequest.model_validate({"question": "x" * 2001})


def test_ask_request_rejects_control_characters_only() -> None:
    with pytest.raises(ValidationError):
        AskRequest.model_validate({"question": "\x00\x01\x02"})


def test_ask_request_normalizes_and_preserves_unicode() -> None:
    assert AskRequest.model_validate({"question": "  métabolite\tドラッグ\n "}).question == (
        "métabolite ドラッグ"
    )


def test_translate_provider_error_codes() -> None:
    assert isinstance(
        translate_provider_error(
            ProviderProtocolError("bad key", retryable=False, code="configuration_error")
        ),
        ConfigurationError,
    )
    assert isinstance(
        translate_provider_error(
            ProviderProtocolError("limited", retryable=True, code="rate_limited")
        ),
        RateLimitError,
    )
    assert isinstance(
        translate_provider_error(
            ProviderProtocolError("slow", retryable=True, code="provider_timeout")
        ),
        ProviderTimeoutError,
    )
    assert isinstance(
        translate_provider_error(
            ProviderProtocolError("down", retryable=True, code="provider_error")
        ),
        ProviderError,
    )
