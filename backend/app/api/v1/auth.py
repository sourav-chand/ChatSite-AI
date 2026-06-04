"""Auth API router."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from app.core.dependencies import DbSession, get_redis
from app.core.rate_limit import limiter
from app.schemas.auth import (
    ForgotPasswordIn,
    RefreshIn,
    ResetPasswordIn,
    UserLogin,
    UserRegister,
    VerifyEmailIn,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Auth"])


def _service(
    session: DbSession,
    redis = Depends(get_redis),
) -> AuthService:
    return AuthService(session=session, redis=redis)


@router.post("/register", status_code=201)
@limiter.limit("5/minute")
async def register(request: Request, payload: UserRegister, service: AuthService = Depends(_service)):
    return await service.register(payload)


@router.post("/login")
@limiter.limit("5/minute")
async def login(request: Request, payload: UserLogin, service: AuthService = Depends(_service)):
    token, _ = await service.login(payload)
    return {"data": token.model_dump()}


@router.post("/refresh")
@limiter.limit("10/minute")
async def refresh(
    request: Request,
    payload: RefreshIn,
    service: AuthService = Depends(_service),
):
    from app.auth.jwt_tokens import verify_access_token
    from app.core.exceptions import UnauthorizedError

    try:
        claims = verify_access_token(payload.refresh_token)
    except Exception as exc:
        raise UnauthorizedError("Invalid refresh token") from exc
    pair, _ = await service.refresh(payload.refresh_token, claims.jti, claims.user_id, claims.workspace_id)
    return {"data": pair.model_dump()}


@router.post("/logout", status_code=204)
async def logout(request: Request, service: AuthService = Depends(_service)):
    principal = getattr(request.state, "principal", None)
    if principal is None:
        return
    from app.services.auth_service import AuthContext

    ctx = AuthContext(
        user_id=principal.user_id, workspace_id=principal.workspace_id, role=principal.role
    )
    await service.logout(ctx, principal.jti)


@router.post("/forgot-password", status_code=202)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request, payload: ForgotPasswordIn, service: AuthService = Depends(_service)
):
    await service.forgot_password(payload.email)
    return {"data": {"ok": True}}


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    request: Request, payload: ResetPasswordIn, service: AuthService = Depends(_service)
):
    await service.reset_password(payload.token, payload.new_password)
    return {"data": {"ok": True}}


@router.post("/verify-email")
@limiter.limit("10/minute")
async def verify_email(
    request: Request, payload: VerifyEmailIn, service: AuthService = Depends(_service)
):
    await service.verify_email(payload.token)
    return {"data": {"ok": True}}
