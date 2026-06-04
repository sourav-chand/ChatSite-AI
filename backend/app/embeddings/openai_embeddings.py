"""OpenAI embeddings + Google Gemini fallback wrapper with batch processing."""
from __future__ import annotations

import asyncio
from typing import Iterable

import structlog
from openai import AsyncOpenAI

from app.core.config import settings

log = structlog.get_logger(__name__)

BATCH_SIZE = 100


class EmbeddingService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = settings.OPENAI_MODEL_EMBED

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = [t if t else " " for t in texts[i : i + BATCH_SIZE]]
            try:
                resp = await self.client.embeddings.create(model=self.model, input=batch)
                out.extend([d.embedding for d in resp.data])
            except Exception as exc:
                log.error("embedding.batch_failed", offset=i, error=str(exc))
                raise
        return out

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]


class GoogleEmbeddingFallback:
    def __init__(self) -> None:
        import google.generativeai as genai

        genai.configure(api_key=settings.GOOGLE_API_KEY)
        self.model = "models/text-embedding-004"

    async def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        loop = asyncio.get_event_loop()
        for t in texts:
            r = await loop.run_in_executor(None, lambda: __import__("google.generativeai", fromlist=["embed_content"]).embed_content(model=self.model, content=t))
            out.append(r["embedding"])
        return out
