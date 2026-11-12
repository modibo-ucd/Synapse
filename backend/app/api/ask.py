"""POST /ask and POST /ask/stream endpoints (thin routers)."""

from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import cast

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from app.agent.events import StageEvent
from app.core.errors import AppError, error_response
from app.core.logging import get_request_id
from app.schemas.domain import AskRequest, AskResponse
from app.services.ask_service import AskService

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
async def ask(request: Request, body: AskRequest) -> AskResponse:
    service = cast(AskService, request.app.state.ask_service)
    return await service.ask(body.question, get_request_id())


@router.post("/ask/stream")
async def ask_stream(request: Request, body: AskRequest) -> StreamingResponse:
    """Stream stage events (SSE) and then the final result; cancel on disconnect."""
    service = cast(AskService, request.app.state.ask_service)
    trace_id = get_request_id() or ""

    async def event_stream() -> AsyncIterator[str]:
        queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

        async def emit(event: StageEvent) -> None:
            await queue.put(("stage", event.model_dump_json()))

        async def run_and_finish() -> None:
            try:
                result = await service.ask_streaming(body.question, trace_id, emit)
                await queue.put(("result", result.model_dump_json()))
            except AppError as exc:
                await queue.put(
                    ("error", json.dumps(error_response(exc.code, exc.message, trace_id)))
                )
            except Exception:  # noqa: BLE001 - never leak internals over SSE
                await queue.put(
                    (
                        "error",
                        json.dumps(
                            error_response("internal_error", "Internal server error.", trace_id)
                        ),
                    )
                )
            finally:
                await queue.put(None)

        task = asyncio.create_task(run_and_finish())
        try:
            while True:
                item = await queue.get()
                if item is None:
                    break
                kind, data = item
                yield f"event: {kind}\ndata: {data}\n\n"
        finally:
            if not task.done():
                task.cancel()
            try:
                await task
            except (asyncio.CancelledError, Exception):  # noqa: BLE001 - task was cancelled
                pass

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )

