"""Refresh token store backed by Redis. Only SHA-256 hashes are persisted."""
from __future__ import annotations

import hashlib
import secrets
import time
from uuid import UUID

from redis.asyncio import Redis

from app.core.config import settings


def _key(workspace_id: UUID, user_id: UUID, jti: str) -> str:
    return f"ws:{workspace_id}:refresh:{user_id}:{jti}"


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def new_refresh_token() -> tuple[str, str]:
    raw = secrets.token_urlsafe(48)
    return raw, hash_token(raw)


async def store_refresh(redis: Redis, workspace_id: UUID, user_id: UUID, jti: str) -> str:
    raw, hashed = new_refresh_token()
    key = _key(workspace_id, user_id, jti)
    await redis.hset(
        key,
        mapping={"hash": hashed, "iat": str(int(time.time()))},
    )
    await redis.expire(key, settings.JWT_REFRESH_TTL_DAYS * 86400)
    return raw


async def verify_and_revoke(redis: Redis, workspace_id: UUID, user_id: UUID, jti: str, presented: str) -> bool:
    key = _key(workspace_id, user_id, jti)
    record = await redis.hgetall(key)
    if not record:
        return False
    if record.get("hash") != hash_token(presented):
        return False
    await redis.delete(key)
    return True


async def revoke(redis: Redis, workspace_id: UUID, user_id: UUID, jti: str) -> None:
    await redis.delete(_key(workspace_id, user_id, jti))
