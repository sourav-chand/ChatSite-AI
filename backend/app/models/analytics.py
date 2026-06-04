"""Analytics events + daily rollup table."""
from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import INET, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin, UUIDPKMixin


class AnalyticsEvent(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "analytics"
    __table_args__ = (
        Index("ix_analytics_ws_chatbot_type_time", "workspace_id", "chatbot_id", "event_type", "created_at"),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    chatbot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    session_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), index=True, nullable=False)
    data: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    ip_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    page_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    referrer: Mapped[str | None] = mapped_column(String(2048), nullable=True)


class AnalyticsDaily(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "analytics_daily"
    __table_args__ = (
        Index(
            "ix_analytics_daily_ws_chatbot_date",
            "workspace_id",
            "chatbot_id",
            "date",
            unique=True,
        ),
    )

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False
    )
    chatbot_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("chatbots.id", ondelete="CASCADE"), nullable=False
    )
    date: Mapped[date] = mapped_column(Date, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
