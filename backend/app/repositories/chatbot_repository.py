"""Chatbot, conversation, message, lead, analytics repositories."""
from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsDaily, AnalyticsEvent
from app.models.chatbot import Chatbot, Conversation, Lead, Message, MessageRole


class ChatbotRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_workspace(self, workspace_id: UUID) -> list[Chatbot]:
        result = await self.session.execute(
            select(Chatbot).where(
                Chatbot.workspace_id == workspace_id, Chatbot.is_deleted.is_(False)
            )
        )
        return list(result.scalars().all())

    async def get(self, workspace_id: UUID, chatbot_id: UUID) -> Chatbot | None:
        result = await self.session.execute(
            select(Chatbot).where(
                Chatbot.id == chatbot_id,
                Chatbot.workspace_id == workspace_id,
                Chatbot.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_slug(self, slug: str) -> Chatbot | None:
        result = await self.session.execute(select(Chatbot).where(Chatbot.slug == slug))
        return result.scalar_one_or_none()

    async def get_by_slug_or_id(self, slug: str, bot_id: UUID) -> Chatbot | None:
        result = await self.session.execute(
            select(Chatbot).where((Chatbot.slug == slug) | (Chatbot.id == bot_id))
        )
        return result.scalar_one_or_none()

    async def create(self, **values) -> Chatbot:
        bot = Chatbot(**values)
        self.session.add(bot)
        await self.session.commit()
        await self.session.refresh(bot)
        return bot

    async def update(self, bot: Chatbot, values: dict) -> Chatbot:
        for k, v in values.items():
            if v is not None:
                setattr(bot, k, v)
        await self.session.commit()
        await self.session.refresh(bot)
        return bot

    async def soft_delete(self, bot: Chatbot) -> None:
        bot.is_deleted = True
        await self.session.commit()


class ConversationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_or_create(
        self,
        *,
        chatbot_id: UUID,
        workspace_id: UUID,
        session_id: UUID,
        page_url: str | None,
        metadata: dict,
    ) -> Conversation:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.chatbot_id == chatbot_id,
                Conversation.session_id == session_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv:
            return conv
        conv = Conversation(
            chatbot_id=chatbot_id,
            workspace_id=workspace_id,
            session_id=session_id,
            page_url=page_url,
            metadata_json=metadata,
        )
        self.session.add(conv)
        await self.session.commit()
        await self.session.refresh(conv)
        return conv

    async def get(self, workspace_id: UUID, conversation_id: UUID) -> Conversation | None:
        result = await self.session.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.workspace_id == workspace_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_for_chatbot(
        self, workspace_id: UUID, chatbot_id: UUID, page: int, page_size: int
    ) -> tuple[list[Conversation], int]:
        base = select(Conversation).where(
            Conversation.workspace_id == workspace_id,
            Conversation.chatbot_id == chatbot_id,
        )
        total = await self.session.execute(
            select(func.count()).select_from(base.subquery())
        )
        items = await self.session.execute(
            base.order_by(Conversation.started_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items.scalars().all()), int(total.scalar_one())

    async def increment_message_count(self, conv_id: UUID) -> None:
        await self.session.execute(
            Conversation.__table__.update()
            .where(Conversation.id == conv_id)
            .values(message_count=Conversation.message_count + 1)
        )
        await self.session.commit()

    async def attach_lead(self, conv_id: UUID, lead_id: UUID) -> None:
        await self.session.execute(
            Conversation.__table__.update()
            .where(Conversation.id == conv_id)
            .values(lead_id=lead_id)
        )
        await self.session.commit()

    async def end(self, conv_id: UUID) -> None:
        await self.session.execute(
            Conversation.__table__.update()
            .where(Conversation.id == conv_id)
            .values(ended_at=datetime.utcnow())
        )
        await self.session.commit()


class MessageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add(
        self,
        *,
        conversation_id: UUID,
        role: MessageRole,
        content: str,
        sources: list | None = None,
        model_used: str | None = None,
        tokens_prompt: int = 0,
        tokens_completion: int = 0,
        latency_ms: int = 0,
        confidence: str | None = None,
    ) -> Message:
        msg = Message(
            conversation_id=conversation_id,
            role=role,
            content=content,
            sources=sources or [],
            model_used=model_used,
            tokens_prompt=tokens_prompt,
            tokens_completion=tokens_completion,
            latency_ms=latency_ms,
            confidence=confidence,
        )
        self.session.add(msg)
        await self.session.commit()
        await self.session.refresh(msg)
        return msg

    async def list_for_conversation(self, conversation_id: UUID) -> list[Message]:
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.created_at)
        )
        return list(result.scalars().all())


class LeadRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **values) -> Lead:
        lead = Lead(**values)
        self.session.add(lead)
        await self.session.commit()
        await self.session.refresh(lead)
        return lead

    async def list_for_chatbot(
        self, workspace_id: UUID, chatbot_id: UUID, page: int, page_size: int
    ) -> tuple[list[Lead], int]:
        base = select(Lead).where(
            Lead.workspace_id == workspace_id,
            Lead.chatbot_id == chatbot_id,
        )
        total = await self.session.execute(
            select(func.count()).select_from(base.subquery())
        )
        items = await self.session.execute(
            base.order_by(Lead.captured_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(items.scalars().all()), int(total.scalar_one())

    async def get(self, workspace_id: UUID, lead_id: UUID) -> Lead | None:
        return await self.session.get(Lead, lead_id)

    async def delete(self, lead: Lead) -> None:
        await self.session.delete(lead)
        await self.session.commit()


class AnalyticsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def insert_event(self, **values) -> AnalyticsEvent:
        ev = AnalyticsEvent(**values)
        self.session.add(ev)
        await self.session.commit()
        return ev

    async def query_events(
        self,
        workspace_id: UUID,
        chatbot_id: UUID | None,
        event_type: str | None,
        start: datetime,
        end: datetime,
        limit: int = 500,
    ) -> list[AnalyticsEvent]:
        stmt = select(AnalyticsEvent).where(
            AnalyticsEvent.workspace_id == workspace_id,
            AnalyticsEvent.created_at >= start,
            AnalyticsEvent.created_at <= end,
        )
        if chatbot_id:
            stmt = stmt.where(AnalyticsEvent.chatbot_id == chatbot_id)
        if event_type:
            stmt = stmt.where(AnalyticsEvent.event_type == event_type)
        stmt = stmt.order_by(AnalyticsEvent.created_at.desc()).limit(limit)
        return list((await self.session.execute(stmt)).scalars().all())

    async def upsert_daily(self, *, workspace_id: UUID, chatbot_id: UUID, day: date, metrics: dict) -> None:
        stmt = (
            pg_insert(AnalyticsDaily)
            .values(workspace_id=workspace_id, chatbot_id=chatbot_id, date=day, metrics=metrics)
            .on_conflict_do_update(
                index_elements=["workspace_id", "chatbot_id", "date"],
                set_={"metrics": metrics, "updated_at": func.now()},
            )
        )
        await self.session.execute(stmt)
        await self.session.commit()

    async def summary(
        self, workspace_id: UUID, chatbot_id: UUID | None, since: datetime
    ) -> dict:
        base = select(AnalyticsEvent).where(
            AnalyticsEvent.workspace_id == workspace_id,
            AnalyticsEvent.created_at >= since,
        )
        if chatbot_id:
            base = base.where(AnalyticsEvent.chatbot_id == chatbot_id)

        events = list((await self.session.execute(base)).scalars().all())

        unique_visitors = len({e.session_id for e in events if e.event_type == "page_view"})
        total_conversations = sum(1 for e in events if e.event_type == "conversation_start")
        total_messages = sum(1 for e in events if e.event_type == "message_sent")
        leads_generated = sum(1 for e in events if e.event_type == "lead_captured")
        conversion_rate = (
            (leads_generated / total_conversations * 100) if total_conversations else 0.0
        )
        avg_messages = (total_messages / total_conversations) if total_conversations else 0.0
        latencies = [
            (e.data or {}).get("latency_ms", 0)
            for e in events
            if e.event_type == "message_sent"
        ]
        avg_latency = (sum(latencies) / len(latencies)) if latencies else 0.0
        tokens = sum(
            (e.data or {}).get("tokens_total", 0) for e in events if e.event_type == "message_sent"
        )
        cost = (tokens / 1000.0) * 0.005
        return {
            "unique_visitors": unique_visitors,
            "total_conversations": total_conversations,
            "total_messages": total_messages,
            "leads_generated": leads_generated,
            "conversion_rate": round(conversion_rate, 2),
            "avg_messages_per_conversation": round(avg_messages, 2),
            "avg_response_latency_ms": round(avg_latency, 2),
            "token_usage_total": tokens,
            "estimated_cost_usd": round(cost, 4),
        }
