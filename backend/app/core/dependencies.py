"""Shared FastAPI dependencies."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt_tokens import AccessClaims, verify_access_token
from app.core.exceptions import UnauthorizedError
from app.database.session import get_session


async def db_session() -> AsyncSession:  # type: ignore[misc]
    async for s in get_session():
        yield s


DbSession = Annotated[AsyncSession, Depends(db_session)]


def _extract_bearer(authorization: str | None) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise UnauthorizedError("Missing bearer token")
    return authorization.split(" ", 1)[1].strip()


async def current_principal(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> AccessClaims:
    token = _extract_bearer(authorization)
    claims = verify_access_token(token)
    request.state.principal = claims
    request.state.workspace_id = claims.workspace_id
    request.state.user_id = claims.user_id
    return claims


CurrentPrincipal = Annotated[AccessClaims, Depends(current_principal)]


def require_role(*allowed: str):
    async def _dep(principal: CurrentPrincipal) -> AccessClaims:
        if principal.role not in allowed:
            from app.core.exceptions import ForbiddenError

            raise ForbiddenError(f"Role {principal.role} not permitted")
        return principal

    return _dep


async def workspace_id_from_request(request: Request) -> UUID:
    ws = getattr(request.state, "workspace_id", None)
    if ws is None:
        raise UnauthorizedError("Workspace context missing")
    return ws
