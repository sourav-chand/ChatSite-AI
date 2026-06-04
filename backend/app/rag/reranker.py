"""Cross-encoder reranker using sentence-transformers ms-marco model."""
from __future__ import annotations

import asyncio
from typing import Sequence

import structlog

log = structlog.get_logger(__name__)

_MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"
_model = None
_lock = asyncio.Lock()


async def _get_model():
    global _model
    async with _lock:
        if _model is None:
            from sentence_transformers import CrossEncoder

            _model = CrossEncoder(_MODEL_NAME)
        return _model


async def rerank(query: str, candidates: Sequence[dict], top_k: int = 4) -> list[dict]:
    """Returns top_k candidates sorted by cross-encoder score (desc)."""
    if not candidates:
        return []
    try:
        model = await _get_model()
    except Exception as exc:
        log.warning("reranker.unavailable_falling_back", error=str(exc))
        return sorted(candidates, key=lambda c: c.get("score", 0.0), reverse=True)[:top_k]

    pairs = [(query, c.get("content", "")) for c in candidates]
    loop = asyncio.get_event_loop()
    scores = await loop.run_in_executor(None, model.predict, pairs)
    for c, s in zip(candidates, scores):
        c["rerank_score"] = float(s)
    return sorted(candidates, key=lambda c: c["rerank_score"], reverse=True)[:top_k]
