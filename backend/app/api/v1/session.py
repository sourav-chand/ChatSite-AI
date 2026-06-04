"""Cookie-based session refresh handler — frontend sets HttpOnly cookies."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request, Response
from redis.asyncio import Redis

from app.auth import jwt_tokens, refresh_tokens
from app.core.dependencies import get_redis
from app.core.exceptions import UnauthorizedError
from app.schemas.auth import TokenPair

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/session/refresh")
async def session_refresh(
    request: Request,
    response: Response,
    redis: Redis = Depends(get_redis),
):
    presented = request.cookies.get("cs_refresh")
    jti = request.cookies.get("cs_jti")
    if not presented or not jti:
        raise UnauthorizedError("Missing refresh cookies")

    try:
        claims = jwt_tokens.verify_access_token(presented)
    except Exception as exc:
        raise UnauthorizedError("Bad refresh token") from exc

    ok = await refresh_tokens.verify_and_revoke(
        redis, claims.workspace_id, claims.user_id, jti, presented
    )
    if not ok:
        raise UnauthorizedError("Refresh rejected")

    new_access, ttl = jwt_tokens.issue_access_token(
        claims.user_id, claims.workspace_id, claims.role
    )
    new_raw = await refresh_tokens.store_refresh(redis, claims.workspace_id, claims.user_id, jti)
    response.set_cookie("cs_refresh", new_raw, httponly=True, secure=True, samesite="strict")
    response.set_cookie("cs_jti", jti, httponly=True, secure=True, samesite="strict")
    return {"data": TokenPair(access_token=new_access, refresh_token=new_raw, expires_in=ttl).model_dump()}
