"""GET /api/v1/sources and /api/v1/sources/{file_name} (read-only)."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request, Response

from app.schemas.sources import SourceDocument, SourceSummary
from app.services.source_service import SourceService

router = APIRouter(prefix="/api/v1/sources", tags=["sources"])

_CACHE_CONTROL = "public, max-age=3600"


def _etag_matches(header: str | None, etag: str) -> bool:
    """Weak-compare an ``If-None-Match`` header against a weak ETag."""
    if not header:
        return False
    target = etag.removeprefix("W/").strip('"')
    for candidate in header.split(","):
        candidate = candidate.strip().removeprefix("W/").strip('"')
        if candidate == target or candidate == "*":
            return True
    return False


@router.get("", response_model=list[SourceSummary])
async def list_sources(request: Request, response: Response) -> list[SourceSummary]:
    service = cast(SourceService, request.app.state.source_service)
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return service.list_files()


@router.get("/{file_name}", response_model=SourceDocument)
async def get_source(
    file_name: str, request: Request, response: Response
) -> SourceDocument | Response:
    service = cast(SourceService, request.app.state.source_service)
    document, etag = service.get(file_name)
    if _etag_matches(request.headers.get("If-None-Match"), etag):
        return Response(
            status_code=304, headers={"ETag": etag, "Cache-Control": _CACHE_CONTROL}
        )
    response.headers["ETag"] = etag
    response.headers["Cache-Control"] = _CACHE_CONTROL
    return document
