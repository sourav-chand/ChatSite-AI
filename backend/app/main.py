"""ChatSite AI — FastAPI application entry point."""
from __future__ import annotations

import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.v1 import api_router
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.logging import configure_logging
from app.core.rate_limit import limiter
from app.database.session import engine
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.middleware.workspace import WorkspaceMiddleware

log = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging(settings.ENVIRONMENT)
    log.info("app.startup", environment=settings.ENVIRONMENT, version="1.0.0")
    yield
    await engine.dispose()
    log.info("app.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="ChatSite AI API",
        version="1.0.0",
        description="Multi-tenant RAG chatbot SaaS",
        docs_url="/docs" if settings.ENVIRONMENT != "prod" else None,
        redoc_url="/redoc" if settings.ENVIRONMENT != "prod" else None,
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(WorkspaceMiddleware)

    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "data": None,
                "error": {"code": exc.code, "message": exc.message, "details": exc.details},
            },
        )

    @app.get("/health", tags=["meta"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    app.include_router(api_router, prefix="/api/v1")
    return app


app = create_app()
