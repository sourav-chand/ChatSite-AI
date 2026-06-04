"""Full RAG pipeline orchestrator."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import AsyncIterator
from uuid import UUID

import structlog

from app.core.config import settings
from app.embeddings.llm_gateway import LLMGateway
from app.embeddings.openai_embeddings import EmbeddingService
from app.models.chatbot import Chatbot
from app.qdrant.client import QdrantService
from app.rag.prompt import build_prompt, detect_injection, validate_query
from app.rag.reranker import rerank

log = structlog.get_logger(__name__)


@dataclass(slots=True)
class RAGAnswer:
    response: str
    sources: list[dict]
    confidence: str
    suggested_questions: list[str]
    model_used: str
    latency_ms: int
    tokens_prompt: int
    tokens_completion: int


class RAGPipeline:
    def __init__(
        self,
        *,
        embedder: EmbeddingService,
        qdrant: QdrantService,
        llm: LLMGateway,
    ) -> None:
        self.embedder = embedder
        self.qdrant = qdrant
        self.llm = llm

    async def _retrieve(
        self,
        *,
        chatbot: Chatbot,
        question: str,
    ) -> list[dict]:
        query_vec = await self.embedder.embed_one(question)
        candidates = await self.qdrant.search(
            chatbot.workspace_id,
            query_vec,
            top_k=settings.RAG_TOP_K,
            score_threshold=settings.RAG_SCORE_THRESHOLD,
            website_id=chatbot.website_id,
        )
        rag_cfg = (chatbot.settings or {}).get("rag", {})
        if rag_cfg.get("rerank", True):
            candidates = await rerank(question, candidates, top_k=settings.RAG_RERANK_TOP_K)
        return candidates

    @staticmethod
    def _confidence(top_score: float) -> str:
        if top_score >= 0.88:
            return "high"
        if top_score >= 0.72:
            return "medium"
        return "low"

    async def answer(
        self,
        *,
        chatbot: Chatbot,
        message: str,
        history: list[dict],
    ) -> RAGAnswer:
        clean = validate_query(message)
        start = time.perf_counter()
        chunks = await self._retrieve(chatbot=chatbot, question=clean)
        bundle = build_prompt(
            company_name=chatbot.name,
            chunks=chunks,
            history=history,
            question=clean,
        )
        result = await self.llm.chat(
            messages=[
                {"role": "system", "content": bundle.system},
                {"role": "user", "content": bundle.user},
            ]
        )
        latency = int((time.perf_counter() - start) * 1000)
        top_score = chunks[0]["score"] if chunks else 0.0
        return RAGAnswer(
            response=result.content,
            sources=[
                {
                    "url": c.get("source_url"),
                    "title": c.get("title"),
                    "score": float(c.get("rerank_score", c.get("score", 0.0))),
                }
                for c in chunks
            ],
            confidence=self._confidence(top_score),
            suggested_questions=[],
            model_used=result.model,
            latency_ms=latency,
            tokens_prompt=result.tokens_prompt,
            tokens_completion=result.tokens_completion,
        )

    async def stream(
        self,
        *,
        chatbot: Chatbot,
        message: str,
        history: list[dict],
    ) -> tuple[AsyncIterator[str], list[dict], str, int]:
        clean = validate_query(message)
        chunks = await self._retrieve(chatbot=chatbot, question=clean)
        bundle = build_prompt(
            company_name=chatbot.name,
            chunks=chunks,
            history=history,
            question=clean,
        )
        stream_iter = await self.llm.chat(
            messages=[
                {"role": "system", "content": bundle.system},
                {"role": "user", "content": bundle.user},
            ],
            stream=True,
        )
        top_score = chunks[0]["score"] if chunks else 0.0
        confidence = self._confidence(top_score)
        sources = [
            {
                "url": c.get("source_url"),
                "title": c.get("title"),
                "score": float(c.get("rerank_score", c.get("score", 0.0))),
            }
            for c in chunks
        ]
        return stream_iter, sources, confidence, len(chunks)
