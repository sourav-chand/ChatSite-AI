"""Conversation browser endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core.dependencies import CurrentPrincipal, DbSession
from app.core.exceptions import NotFoundError
from app.repositories.chatbot_repository import ConversationRepository, MessageRepository
from app.schemas.common import PageMeta

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.get("")
async def list_conversations(
    principal: CurrentPrincipal,
    session: DbSession,
    chatbot_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    from uuid import UUID

    repo = ConversationRepository(session)
    items, total = await repo.list_for_chatbot(principal.workspace_id, UUID(chatbot_id), page, page_size)
    return {
        "data": [
            {
                "id": str(c.id),
                "chatbot_id": str(c.chatbot_id),
                "session_id": str(c.session_id),
                "started_at": c.started_at.isoformat(),
                "ended_at": c.ended_at.isoformat() if c.ended_at else None,
                "message_count": c.message_count,
                "page_url": c.page_url,
            }
            for c in items
        ],
        "meta": PageMeta(page=page, page_size=page_size, total=total).model_dump(),
    }


@router.get("/{conversation_id}")
async def get_conversation(conversation_id: str, principal: CurrentPrincipal, session: DbSession):
    from uuid import UUID

    conv = await ConversationRepository(session).get(principal.workspace_id, UUID(conversation_id))
    if not conv:
        raise NotFoundError("Conversation not found")
    return {"data": {"id": str(conv.id), "started_at": conv.started_at.isoformat(), "page_url": conv.page_url}}


@router.get("/{conversation_id}/messages")
async def get_messages(conversation_id: str, principal: CurrentPrincipal, session: DbSession):
    from uuid import UUID

    conv = await ConversationRepository(session).get(principal.workspace_id, UUID(conversation_id))
    if not conv:
        raise NotFoundError("Conversation not found")
    msgs = await MessageRepository(session).list_for_conversation(conv.id)
    return {
        "data": [
            {
                "id": str(m.id),
                "role": m.role.value,
                "content": m.content,
                "sources": m.sources,
                "model_used": m.model_used,
                "created_at": m.created_at.isoformat(),
                "latency_ms": m.latency_ms,
            }
            for m in msgs
        ]
    }
