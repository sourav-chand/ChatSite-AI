"""Redis async client singleton."""
from __future__ import annotations

from redis.asyncio import Redis, from_url

from app.core.config import settings

redis_client: Redis = from_url(
    settings.REDIS_URL,
    encoding="utf-8",
    decode_responses=True,
    max_connections=50,
)


async def get_redis() -> Redis:
    return redis_client
