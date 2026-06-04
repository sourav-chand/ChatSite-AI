"""Chatbot CRUD + embed code generator."""
from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.dependencies import CurrentPrincipal, DbSession
from app.core.exceptions import NotFoundError
from app.repositories.chatbot_repository import ChatbotRepository
from app.schemas.resources import ChatbotCreate, ChatbotUpdate, EmbedCodeOut
from app.services.workspace_service import WebsiteService

router = APIRouter(prefix="/chatbots", tags=["Chatbots"])


@router.get("")
async def list_chatbots(principal: CurrentPrincipal, session: DbSession):
    repo = ChatbotRepository(session)
    items = await repo.list_for_workspace(principal.workspace_id)
    return {"data": [c.__dict__ for c in items]}


@router.post("", status_code=201)
async def create_chatbot(
    payload: ChatbotCreate,
    principal: CurrentPrincipal,
    session: DbSession,
):
    website_svc = WebsiteService(session)
    await website_svc.get(principal.workspace_id, payload.website_id)

    repo = ChatbotRepository(session)
    slug = secrets.token_urlsafe(6).lower().replace("_", "-").replace("+", "")[:16]
    bot = await repo.create(
        workspace_id=principal.workspace_id,
        website_id=payload.website_id,
        name=payload.name,
        slug=slug,
        allowed_domains=payload.allowed_domains,
        settings=payload.settings,
    )
    return {"data": {"id": str(bot.id), "slug": bot.slug}}


@router.get("/{chatbot_id}")
async def get_chatbot(chatbot_id: UUID, principal: CurrentPrincipal, session: DbSession):
    bot = await ChatbotRepository(session).get(principal.workspace_id, chatbot_id)
    if not bot:
        raise NotFoundError("Chatbot not found")
    return {"data": bot.__dict__}


@router.put("/{chatbot_id}")
async def update_chatbot(
    chatbot_id: UUID, payload: ChatbotUpdate, principal: CurrentPrincipal, session: DbSession
):
    bot = await ChatbotRepository(session).get(principal.workspace_id, chatbot_id)
    if not bot:
        raise NotFoundError("Chatbot not found")
    bot = await ChatbotRepository(session).update(bot, payload.model_dump(exclude_none=True))
    return {"data": bot.__dict__}


@router.delete("/{chatbot_id}", status_code=204)
async def delete_chatbot(chatbot_id: UUID, principal: CurrentPrincipal, session: DbSession):
    bot = await ChatbotRepository(session).get(principal.workspace_id, chatbot_id)
    if not bot:
        raise NotFoundError("Chatbot not found")
    await ChatbotRepository(session).soft_delete(bot)


@router.get("/{chatbot_id}/embed-code")
async def embed_code(chatbot_id: UUID, principal: CurrentPrincipal, session: DbSession):
    bot = await ChatbotRepository(session).get(principal.workspace_id, chatbot_id)
    if not bot:
        raise NotFoundError("Chatbot not found")
    cfg = bot.settings or {}
    snippet = (
        f'<script src="{settings.WIDGET_CDN_URL}/widget.js"></script>\n'
        f"<script>\n"
        f"  ChatSite.init({{\n"
        f'    chatbotId: "{bot.id}",\n'
        f'    position: "{cfg.get("position", "bottom-right")}",\n'
        f'    theme: "{cfg.get("theme", "light")}",\n'
        f'    primaryColor: "{cfg.get("primary_color", "#4F46E5")}",\n'
        f'    welcomeMessage: "{cfg.get("welcome_message", "Hi! How can I help?")}",\n'
        f"    suggestedQuestions: {cfg.get('suggested_questions', [])!r}\n"
        f"  }});\n"
        f"</script>"
    )
    return EmbedCodeOut(chatbot_id=bot.id, snippet=snippet).model_dump()
