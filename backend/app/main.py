"""Application factory for the Synapse FastAPI app."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import Response

from app.api.health import router as health_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging, request_id_var
from app.providers import openai as openai_providers
from app.retrieval.index_manager import IndexManager


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure logging and start the in-memory index build in the background."""
    settings: Settings = app.state.settings
    configure_logging(settings.log_level)
    index_manager = IndexManager(settings, openai_providers.build_embedding_provider(settings))
    index_manager.start()
    app.state.index_manager = index_manager
    app.state.index_status = "building"
    try:
        yield
    finally:
        await index_manager.shutdown()


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()

    app = FastAPI(title="Synapse", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.index_status = "building"

    @app.middleware("http")
    async def request_id_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers["X-Request-ID"] = request_id
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    return app


app = create_app()
