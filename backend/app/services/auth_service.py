"""Authentication service — registration, login, JWT rotation, verification."""
from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Annotated
from uuid import UUID

import structlog
from fastapi import Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import jwt_tokens, passwords, refresh_tokens
from app.core.dependencies import DbSession, get_redis
from app.core.email import render_template, send_email
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UnauthorizedError,
    ValidationFailedError,
)
from app.repositories.user_repository import UserRepository
from app.schemas.auth import TokenPair, UserLogin, UserRegister

log = structlog.get_logger(__name__)


@dataclass(slots=True)
class AuthContext:
    user_id: UUID
    workspace_id: UUID
    role: str


class AuthService:
    def __init__(
        self,
        session: Annotated[AsyncSession, Depends(DbSession)],
        redis: Annotated[Redis, Depends(get_redis)],
    ) -> None:
        self.session = session
        self.redis = redis
        self.users = UserRepository(session)

    async def register(self, payload: UserRegister) -> dict:
        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise ConflictError("Email already registered")

        user = await self.users.create(
            email=payload.email,
            password_hash=passwords.hash_password(payload.password),
            full_name=payload.full_name,
        )

        verify_token = jwt_tokens.issue_short_lived_token(
            {"sub": str(user.id), "purpose": "verify"}, ttl_seconds=86400
        )
        await send_email(
            "Verify your ChatSite AI account",
            [user.email],
            render_template("verify", token=verify_token),
        )
        return {"user_id": str(user.id), "verification_email_sent": True}

    async def login(self, payload: UserLogin) -> tuple[TokenPair, AuthContext]:
        user = await self.users.get_by_email(payload.email)
        if not user or not passwords.verify_password(payload.password, user.password_hash):
            raise UnauthorizedError("Invalid credentials")
        if not user.is_active:
            raise UnauthorizedError("Account disabled")
        if not user.is_verified:
            raise ValidationFailedError("Email not verified")

        await self.users.touch_last_login(user.id)

        workspace_id = await self._primary_workspace(user.id)
        if not workspace_id:
            raise ValidationFailedError("No workspace associated with user")

        return await self._issue_token_pair(user.id, workspace_id, "OWNER")

    async def logout(self, ctx: AuthContext, jti: str) -> None:
        await refresh_tokens.revoke(self.redis, ctx.workspace_id, ctx.user_id, jti)

    async def refresh(self, presented_refresh: str, jti: str, user_id: UUID, workspace_id: UUID) -> TokenPair:
        ok = await refresh_tokens.verify_and_revoke(
            self.redis, workspace_id, user_id, jti, presented_refresh
        )
        if not ok:
            raise UnauthorizedError("Invalid or expired refresh token")
        return (await self._issue_token_pair(user_id, workspace_id, "OWNER"))[0]

    async def verify_email(self, token: str) -> None:
        try:
            payload = jwt_tokens.verify_access_token(token)
        except Exception:
            raise ValidationFailedError("Invalid verification token")
        if payload.role != "verify":
            raise ValidationFailedError("Token purpose mismatch")
        await self.users.mark_verified(payload.user_id)

    async def forgot_password(self, email: str) -> None:
        user = await self.users.get_by_email(email)
        if not user:
            return
        token = jwt_tokens.issue_short_lived_token(
            {"sub": str(user.id), "purpose": "reset"}, ttl_seconds=3600
        )
        await send_email(
            "Reset your ChatSite AI password",
            [user.email],
            render_template("reset", token=token),
        )

    async def reset_password(self, token: str, new_password: str) -> None:
        try:
            payload = jwt_tokens.verify_access_token(token)
        except Exception as exc:
            raise ValidationFailedError("Invalid reset token") from exc
        if payload.role != "reset":
            raise ValidationFailedError("Token purpose mismatch")
        await self.users.update_password(payload.user_id, passwords.hash_password(new_password))

    async def _issue_token_pair(self, user_id: UUID, workspace_id: UUID, role: str) -> tuple[TokenPair, AuthContext]:
        access_token, ttl = jwt_tokens.issue_access_token(user_id, workspace_id, role)
        jti = secrets.token_urlsafe(8)
        refresh_raw = await refresh_tokens.store_refresh(self.redis, workspace_id, user_id, jti)
        token_pair = TokenPair(access_token=access_token, refresh_token=refresh_raw, expires_in=ttl)
        return token_pair, AuthContext(user_id=user_id, workspace_id=workspace_id, role=role)

    async def _primary_workspace(self, user_id: UUID) -> UUID | None:
        from app.models.workspace import Workspace, WorkspaceMember

        result = await self.session.execute(
            __import__("sqlalchemy").select(Workspace.id)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id)
            .order_by(Workspace.created_at.asc())
            .limit(1)
        )
        row = result.first()
        return row[0] if row else None
