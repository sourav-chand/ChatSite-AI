"""Workspace context middleware. Sets per-request workspace id and RLS GUC."""
from __future__ import annotations

from uuid import UUID

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings
from app.database.session import AsyncSessionLocal


PUBLIC_PATH_PREFIXES = (
    "/api/v1/auth",
    "/api/v1/chat/query",
    "/api/v1/chat/stream",
    "/api/v1/health",
    "/docs",
    "/redoc",
    "/openapi.json",
    "/widget.js",
    "/api/v1/widget",
)


class WorkspaceMiddleware(BaseHTTPMiddleware):
    """Resolves workspace from JWT and primes PostgreSQL session GUC for RLS."""

    async def dispatch(self, request: Request, call_next) -> Response:
        request.state.workspace_id = None
        request.state.user_id = None
        request.state.principal = None

        if not request.url.path.startswith("/api/v1/"):
            return await call_next(request)

        if any(request.url.path.startswith(p) for p in PUBLIC_PATH_PREFIXES):
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        if not auth:
            return await call_next(request)

        from app.auth.jwt_tokens import verify_access_token

        try:
            token = auth.split(" ", 1)[1]
            claims = verify_access_token(token)
        except Exception:
            return await call_next(request)

        request.state.principal = claims
        request.state.workspace_id = claims.workspace_id
        request.state.user_id = claims.user_id

        async with AsyncSessionLocal() as session:
            await session.execute(
                __import__("sqlalchemy").text("SELECT set_config('app.current_workspace', :ws, true)"),
                {"ws": str(claims.workspace_id)},
            )

        return await call_next(request)
