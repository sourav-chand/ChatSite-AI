"""Chatbot, conversation, message, lead models."""
from __future__ import annotations

import enum
from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    DateTime,
    Enum as SAEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, SoftDeleteMixin, TimestampMixin, UUIDPKMixin


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class Chatbot(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "chatbots"

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    website_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)
    allowed_domains: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    settings: Mapped[dict] = mapped_column(
        JSONB,
        default=lambda: {
            "theme": "light",
            "position": "bottom-right",
            "primary_color": "#4F46E5",
            "welcome_message": "Hi! How can I help?",
            "suggested_questions": [],
            "lead_capture": {
                "enabled": True,
                "trigger": "after_n_messages",
                "trigger_after": 3,
                "fields": {"name": True, "email": True, "phone": False, "company": False},
            },
            "rag": {
                "rewrite_query": True,
                "multi_query": False,
                "rerank": True,
                "compress": True,
                "model": "gpt-4o",
            },
        },
        nullable=False,
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="chatbots")  # type: ignore[name-defined]
    website: Mapped["Website"] = relationship(back_populates="chatbots")  # type: ignore[name-defined]
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="chatbot", cascade="all, delete-orphan"
    )


class Conversation(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "conversations"
    __table_args__ = (Index("ix_conv_chatbot_started", "chatbot_id", "started_at"),)

    chatbot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    session_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True, nullable=False)
    visitor_id: Mapped[UUID | None] = mapped_column(PG_UUID(as_uuid=True), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    message_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lead_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("leads.id", ondelete="SET NULL"), nullable=True
    )
    page_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSONB, default=dict, nullable=False)

    chatbot: Mapped["Chatbot"] = relationship(back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at"
    )
    lead: Mapped["Lead | None"] = relationship(foreign_keys=[lead_id])  # type: ignore[name-defined]


class Message(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "messages"

    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole, name="message_role"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    sources: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    model_used: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tokens_prompt: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tokens_completion: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    confidence: Mapped[str | None] = mapped_column(String(16), nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="messages")


class Lead(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "leads"
    __table_args__ = (Index("ix_leads_ws_chatbot_captured", "workspace_id", "chatbot_id", "captured_at"),)

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chatbot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False, index=True
    )
    conversation_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False
    )
    session_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_page_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    source_page_title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    chat_transcript: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    utm_params: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    captured_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    workspace: Mapped["Workspace"] = relationship(back_populates="leads")
