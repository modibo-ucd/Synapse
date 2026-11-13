"""Health endpoint (always returns HTTP 200)."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter(tags=["health"])


@router.get("/health")
async def health(request: Request) -> dict[str, object]:
    """Report liveness; never fails, even while indexing or with no LLM key."""
    app = request.app
    manager = getattr(app.state, "index_manager", None)
    index_status = manager.status if manager is not None else app.state.index_status
    chunks = manager.chunks if manager is not None else []
    index_stats: dict[str, object] | None = None
    if chunks:
        index_stats = {
            "files": len({chunk.source_file for chunk in chunks}),
            "chunks": len(chunks),
            "embedding_model": (
                app.state.settings.openai_embedding_model
                if manager is not None and manager.status == "ready"
                else None
            ),
        }
    return {
        "status": "ok",
        "index": index_status,
        "llm_configured": app.state.settings.llm_configured,
        "version": app.state.settings.app_version,
        "index_stats": index_stats,
    }
