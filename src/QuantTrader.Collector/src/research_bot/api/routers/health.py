from __future__ import annotations

from fastapi import APIRouter, Request

from research_bot.api.schemas.common import HealthResponse


router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health(request: Request) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=request.app.state.container.settings.app_name,
    )
