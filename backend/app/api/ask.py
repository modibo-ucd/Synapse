"""POST /ask endpoint (thin router)."""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, Request

from app.core.logging import get_request_id
from app.schemas.domain import AskRequest, AskResponse
from app.services.ask_service import AskService

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
async def ask(request: Request, body: AskRequest) -> AskResponse:
    service = cast(AskService, request.app.state.ask_service)
    return await service.ask(body.question, get_request_id())
