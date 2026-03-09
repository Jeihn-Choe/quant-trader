from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from research_bot.api.routers.analysis import router as analysis_router
from research_bot.api.routers.health import router as health_router
from research_bot.api.routers.market_data import router as market_data_router
from research_bot.bootstrap.container import build_container
from research_bot.bootstrap.settings import Settings


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.container = build_container(settings)
    app.include_router(health_router, prefix="/api")
    app.include_router(market_data_router, prefix="/api")
    app.include_router(analysis_router, prefix="/api")
    return app
