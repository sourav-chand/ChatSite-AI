"""Website + crawled page + chunk models."""
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


class CrawlStatus(str, enum.Enum):
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    DONE = "done"
    FAILED = "failed"


class PageStatus(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"
    SKIPPED = "skipped"


class Website(Base, UUIDPKMixin, TimestampMixin, SoftDeleteMixin):
    __tablename__ = "websites"

    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    favicon_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    crawl_config: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    crawl_status: Mapped[CrawlStatus] = mapped_column(
        SAEnum(CrawlStatus, name="crawl_status"), default=CrawlStatus.IDLE, nullable=False, index=True
    )
    last_crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    pages_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunks_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    workspace: Mapped["Workspace"] = relationship(back_populates="websites")  # type: ignore[name-defined]
    pages: Mapped[list["CrawledPage"]] = relationship(
        back_populates="website", cascade="all, delete-orphan"
    )
    chatbots: Mapped[list["Chatbot"]] = relationship(back_populates="website")


class CrawledPage(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "crawled_pages"
    __table_args__ = (
        Index("ix_pages_workspace_website", "workspace_id", "website_id"),
    )

    website_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    url: Mapped[str] = mapped_column(String(2048), nullable=False)
    canonical_url: Mapped[str] = mapped_column(String(2048), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(String(512), nullable=True)
    meta_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    headings: Mapped[dict] = mapped_column(JSONB, default=dict, nullable=False)
    content: Mapped[str | None] = mapped_column(Text, nullable=True)
    word_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    language: Mapped[str | None] = mapped_column(String(8), nullable=True)
    crawl_status: Mapped[PageStatus] = mapped_column(
        SAEnum(PageStatus, name="page_status"), default=PageStatus.PENDING, nullable=False
    )
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    redirect_chain: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    crawled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    website: Mapped["Website"] = relationship(back_populates="pages")
    chunks: Mapped[list["Chunk"]] = relationship(
        back_populates="page", cascade="all, delete-orphan"
    )


class Chunk(Base, UUIDPKMixin, TimestampMixin):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("ix_chunks_workspace_website_page", "workspace_id", "website_id", "page_id"),
    )

    page_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("crawled_pages.id", ondelete="CASCADE"), nullable=False, index=True
    )
    website_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False, index=True
    )
    workspace_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    token_count: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    total_chunks_in_page: Mapped[int] = mapped_column(Integer, nullable=False)
    heading_context: Mapped[str | None] = mapped_column(String(512), nullable=True)
    embedding_model: Mapped[str] = mapped_column(String(64), nullable=False)
    embedding_dim: Mapped[int] = mapped_column(Integer, default=1536, nullable=False)
    qdrant_point_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False, unique=True)

    page: Mapped["CrawledPage"] = relationship(back_populates="chunks")
