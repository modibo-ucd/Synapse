"""Domain exceptions and their central HTTP handlers.

Services and agent code raise ``AppError`` subclasses; they are mapped to HTTP
responses with a single JSON shape in one place. Handlers never leak stack
traces, prompts, keys or provider payloads.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_request_id

logger = logging.getLogger(__name__)


class AppError(Exception):
    """Base class for all application-level errors."""

    code: str = "internal_error"
    status_code: int = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConfigurationError(AppError):
    """Missing or invalid configuration (e.g. LLM endpoint unreachable)."""

    code = "configuration_error"
    status_code = 503


class ProviderError(AppError):
    """The LLM/embedding provider returned an error."""

    code = "provider_error"
    status_code = 502


class ProviderTimeoutError(AppError):
    """The LLM/embedding provider timed out."""

    code = "provider_timeout"
    status_code = 504


class RateLimitError(AppError):
    """In-process rate limit exceeded."""

    code = "rate_limited"
    status_code = 429


def error_response(code: str, message: str, request_id: str | None) -> dict[str, Any]:
    """Build the single error JSON shape used by every handler."""
    return {"error": {"code": code, "message": message, "request_id": request_id}}


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the app in one central place."""

    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message, get_request_id()),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        _request: Request, _exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response(
                "validation_error", "Invalid request payload.", get_request_id()
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
        logger.error("Unhandled error: %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content=error_response(
                "internal_error", "Internal server error.", get_request_id()
            ),
        )
