"""Application factory for the Synapse FastAPI app."""

from __future__ import annotations

from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.ask import router as ask_router
from app.api.health import router as health_router
from app.api.sources import router as sources_router
from app.core.config import Settings, get_settings
from app.core.errors import NotFoundError, register_exception_handlers
from app.core.logging import configure_logging, request_id_var
from app.providers import openai as openai_providers
from app.retrieval.index_manager import IndexManager
from app.services.ask_service import AskService
from app.services.source_service import SourceService

# Basic hardening headers applied to every response. The CSP allows only the
# built Vite bundle: same-origin scripts/styles/fonts/images, no inline script,
# and no framing of the page. ``'unsafe-inline'`` for styles covers inline style
# attributes used by the UI (Tailwind classes live in the external stylesheet).
SECURITY_HEADERS: dict[str, str] = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "frame-ancestors 'none'; "
        "form-action 'self'"
    ),
}


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Configure logging and start the in-memory index build in the background."""
    settings: Settings = app.state.settings
    configure_logging(
        settings.log_level,
        secrets=(settings.openai_api_key, settings.openai_base_url),
    )
    index_manager = IndexManager(settings, openai_providers.build_embedding_provider(settings))
    index_manager.start()
    app.state.index_manager = index_manager
    app.state.ask_service = AskService(settings, index_manager)
    app.state.source_service = SourceService(settings)
    app.state.index_status = "building"
    try:
        yield
    finally:
        await index_manager.shutdown()


FRONTEND_DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"

# Path prefixes the SPA fallback must never capture: API, docs, and fixed routes.
_SPA_RESERVED_FIRST_SEGMENTS = frozenset(
    {"health", "ask", "docs", "redoc", "openapi.json", "api"}
)


def _is_reserved_path(full_path: str) -> bool:
    """True when the SPA fallback must 404 instead of serving ``index.html``."""
    if not full_path:
        return False
    return full_path.split("/", 1)[0] in _SPA_RESERVED_FIRST_SEGMENTS


def _has_extension(full_path: str) -> bool:
    """True when the last path segment looks like a file (contains a dot)."""
    return "." in full_path.rsplit("/", 1)[-1]


def mount_frontend(app: FastAPI) -> None:
    """Serve the built React UI at / with an SPA fallback when ``dist`` exists.

    Registered after the API routers so /health, /ask, /api/* and the docs routes
    keep precedence. When the build output is absent (local dev) this is a no-op
    and the API still starts normally.
    """
    dist_dir = FRONTEND_DIST_DIR
    index_path = dist_dir / "index.html"
    if not index_path.is_file():
        return

    assets_dir = dist_dir / "assets"
    if assets_dir.is_dir():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    dist_resolved = dist_dir.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa_fallback(full_path: str) -> FileResponse:
        if _is_reserved_path(full_path):
            raise NotFoundError("Not found.")
        if full_path:
            candidate = (dist_resolved / full_path).resolve()
            if candidate.is_relative_to(dist_resolved) and candidate.is_file():
                return FileResponse(candidate)
            if _has_extension(full_path):
                raise NotFoundError("Not found.")
        return FileResponse(index_path)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build and configure the FastAPI application."""
    settings = settings or get_settings()

    app = FastAPI(title="Synapse", version="0.1.0", lifespan=lifespan)
    app.state.settings = settings
    app.state.index_status = "building"
    app.state.source_service = None

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

    @app.middleware("http")
    async def security_headers_middleware(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.update(SECURITY_HEADERS)
        return response

    register_exception_handlers(app)
    app.include_router(health_router)
    app.include_router(ask_router)
    app.include_router(sources_router)
    mount_frontend(app)
    return app


app = create_app()
