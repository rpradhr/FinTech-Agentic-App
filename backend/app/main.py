"""
FastAPI application entry point.

Start with:  uvicorn app.main:app --reload
"""
from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routers import (
    advisory,
    auth_router,
    branches,
    cases,
    chat,
    fraud,
    interactions,
    loans,
)
from app.core.config import get_settings
from app.core.container import Container, set_container
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title="FinTech Agentic Banking Platform",
        description=(
            "Multi-agent banking operations platform: fraud detection, sentiment analysis, "
            "loan review, branch monitoring, and financial advisory — all with human-in-the-loop controls."
        ),
        version="0.1.0",
        docs_url="/docs" if not settings.app_env.value == "production" else None,
        redoc_url="/redoc" if not settings.app_env.value == "production" else None,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Global error handler ──────────────────────────────────────────────────
    @app.exception_handler(KeyError)
    async def key_error_handler(request: Request, exc: KeyError):
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={"detail": str(exc)},
        )

    @app.exception_handler(Exception)
    async def generic_error_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal server error"},
        )

    # ── Routers ───────────────────────────────────────────────────────────────
    app.include_router(auth_router.router)
    app.include_router(fraud.router)
    app.include_router(interactions.router)
    app.include_router(loans.router)
    app.include_router(branches.router)
    app.include_router(advisory.router)
    app.include_router(cases.router)
    app.include_router(chat.router)

    # ── Lifecycle ─────────────────────────────────────────────────────────────
    @app.on_event("startup")
    async def startup():
        logger.info("Starting FinTech Agentic App (env=%s)", settings.app_env)
        container = Container(settings)
        await container.connect()
        set_container(container)
        logger.info("Container initialized — backend=%s", settings.database_backend)

    @app.on_event("shutdown")
    async def shutdown():
        from app.core.container import get_container
        try:
            container = get_container()
            await container.close()
        except RuntimeError:
            pass

    # ── Health check ─────────────────────────────────────────────────────────
    @app.get("/health", tags=["ops"])
    async def health():
        return {"status": "ok", "env": settings.app_env}

    return app


app = create_app()
