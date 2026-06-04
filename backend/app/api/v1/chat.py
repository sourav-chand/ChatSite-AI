"""Public chat API: /chat/query and /chat/stream (SSE)."""
from __future__ import annotations

import json
import time
from datetime import datetime
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DbSession
from app.core.rate_limit import limiter
from app.embeddings.llm_gateway import LLMGateway
from app.embeddings.openai_embeddings import EmbeddingService
from app.models.chatbot import MessageRole
from app.qdrant.client import QdrantService
from app.rag.pipeline import RAGPipeline
from app.repositories.chatbot_repository import (
    ChatbotRepository,
    ConversationRepository,
    MessageRepository,
)
from app.schemas.resources import ChatQueryIn, ChatResponseOut

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat"])


def _build_pipeline() -> RAGPipeline:
    return RAGPipeline(embedder=EmbeddingService(), qdrant=QdrantService(), llm=LLMGateway())


@router.post("/query")
@limiter.limit("30/minute")
async def chat_query(request: Request, payload: ChatQueryIn, session: DbSession):
    bot_repo = ChatbotRepository(session)
    bot = await bot_repo.get_by_slug_or_id(payload.chatbot_id, payload.chatbot_id)
    if not bot or not bot.is_active:
        return JSONResponse(status_code=404, content={"data": None, "error": {"code": "not_found"}})

    conv_repo = ConversationRepository(session)
    msg_repo = MessageRepository(session)
    conv = await conv_repo.get_or_create(
        chatbot_id=bot.id,
        workspace_id=bot.workspace_id,
        session_id=payload.session_id,
        page_url=payload.page_url,
        metadata=payload.metadata,
    )

    pipeline = _build_pipeline()
    answer = await pipeline.answer(chatbot=bot, message=payload.message, history=payload.history)

    await msg_repo.add(
        conversation_id=conv.id,
        role=MessageRole.USER,
        content=payload.message,
    )
    await msg_repo.add(
        conversation_id=conv.id,
        role=MessageRole.ASSISTANT,
        content=answer.response,
        sources=answer.sources,
        model_used=answer.model_used,
        tokens_prompt=answer.tokens_prompt,
        tokens_completion=answer.tokens_completion,
        latency_ms=answer.latency_ms,
        confidence=answer.confidence,
    )
    await conv_repo.increment_message_count(conv.id)

    return {"data": ChatResponseOut(
        response=answer.response,
        sources=answer.sources,
        confidence=answer.confidence,
        suggested_questions=answer.suggested_questions,
        model_used=answer.model_used,
        latency_ms=answer.latency_ms,
    ).model_dump()}


@router.post("/stream")
@limiter.limit("30/minute")
async def chat_stream(request: Request, payload: ChatQueryIn, session: DbSession):
    bot = await ChatbotRepository(session).get_by_slug_or_id(payload.chatbot_id, payload.chatbot_id)
    if not bot or not bot.is_active:
        return JSONResponse(status_code=404, content={"data": None, "error": {"code": "not_found"}})

    conv_repo = ConversationRepository(session)
    msg_repo = MessageRepository(session)
    conv = await conv_repo.get_or_create(
        chatbot_id=bot.id,
        workspace_id=bot.workspace_id,
        session_id=payload.session_id,
        page_url=payload.page_url,
        metadata=payload.metadata,
    )

    pipeline = _build_pipeline()
    start = time.perf_counter()
    stream_iter, sources, confidence, n_chunks = await pipeline.stream(
        chatbot=bot, message=payload.message, history=payload.history
    )

    await msg_repo.add(conversation_id=conv.id, role=MessageRole.USER, content=payload.message)

    async def event_gen():
        full: list[str] = []
        try:
            yield _sse({"type": "meta", "sources": sources, "confidence": confidence})
            async for token in stream_iter:
                if token:
                    full.append(token)
                    yield _sse({"type": "token", "delta": token})
            latency = int((time.perf_counter() - start) * 1000)
            await msg_repo.add(
                conversation_id=conv.id,
                role=MessageRole.ASSISTANT,
                content="".join(full),
                sources=sources,
                model_used=bot.settings.get("rag", {}).get("model", "gpt-4o") if bot.settings else "gpt-4o",
                latency_ms=latency,
                confidence=confidence,
            )
            await conv_repo.increment_message_count(conv.id)
            yield _sse({"type": "done"})
        except Exception as exc:
            log.exception("chat_stream.error", error=str(exc))
            yield _sse({"type": "error", "message": str(exc)})

    return StreamingResponse(event_gen(), media_type="text/event-stream")


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"
