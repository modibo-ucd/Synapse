"""Health endpoint (always returns HTTP 200)."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    """Report liveness; never fails, even while indexing or with no LLM key."""
    app = request.app
    return {
        "status": "ok",
        "index": app.state.index_status,
        "llm_configured": app.state.settings.llm_configured,
    }
