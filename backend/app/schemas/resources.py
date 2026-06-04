"""Workspace, website, chatbot, conversation, lead, analytics schemas."""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from app.models.workspace import WorkspaceRole


class WorkspaceCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    name: str = Field(min_length=2, max_length=255)
    subdomain: str = Field(min_length=3, max_length=63, pattern=r"^[a-z0-9-]+$")
    plan: str = "free"


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=255)
    settings: dict[str, Any] | None = None
    plan: str | None = None


class WorkspaceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID
    name: str
    subdomain: str
    plan: str
    settings: dict[str, Any]
    created_at: datetime


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user_id: UUID
    role: WorkspaceRole
    joined_at: datetime


class WebsiteCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    url: HttpUrl
    name: str = Field(min_length=1, max_length=255)
    crawl_config: dict[str, Any] = Field(default_factory=dict)


class WebsiteUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    crawl_config: dict[str, Any] | None = None
    is_deleted: bool | None = None


class WebsiteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    url: str
    name: str
    favicon_url: str | None
    crawl_status: str
    last_crawled_at: datetime | None
    pages_count: int
    chunks_count: int
    crawl_config: dict[str, Any]


class CrawlStartIn(BaseModel):
    website_id: UUID
    force_recrawl: bool = False


class CrawlStopIn(BaseModel):
    website_id: UUID


class CrawlStatusOut(BaseModel):
    website_id: UUID
    status: str
    pages_found: int
    pages_crawled: int
    pages_failed: int
    chunks_embedded: int
    celery_task_id: str | None


class ChatbotCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    website_id: UUID
    name: str = Field(min_length=1, max_length=255)
    allowed_domains: list[str] = Field(default_factory=list)
    settings: dict[str, Any] = Field(default_factory=dict)


class ChatbotUpdate(BaseModel):
    name: str | None = None
    is_active: bool | None = None
    allowed_domains: list[str] | None = None
    settings: dict[str, Any] | None = None


class ChatbotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    website_id: UUID
    name: str
    slug: str
    is_active: bool
    allowed_domains: list[str]
    settings: dict[str, Any]
    created_at: datetime


class EmbedCodeOut(BaseModel):
    chatbot_id: UUID
    snippet: str


class ChatQueryIn(BaseModel):
    model_config = ConfigDict(strict=True)

    chatbot_id: UUID
    session_id: UUID
    message: str = Field(min_length=1, max_length=500)
    history: list[dict[str, str]] = Field(default_factory=list)
    page_url: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class SourceItem(BaseModel):
    url: str
    title: str | None = None
    score: float


class ChatResponseOut(BaseModel):
    response: str
    sources: list[SourceItem]
    confidence: str
    suggested_questions: list[str] = Field(default_factory=list)
    model_used: str
    latency_ms: int


class ConversationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chatbot_id: UUID
    session_id: UUID
    started_at: datetime
    ended_at: datetime | None
    message_count: int
    lead_id: UUID | None
    page_url: str | None


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    role: str
    content: str
    sources: list[dict[str, Any]]
    model_used: str | None
    tokens_prompt: int
    tokens_completion: int
    latency_ms: int
    confidence: str | None
    created_at: datetime


class LeadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    chatbot_id: UUID
    name: str | None
    email: str | None
    phone: str | None
    company: str | None
    source_page_url: str | None
    captured_at: datetime


class AnalyticsSummaryOut(BaseModel):
    period: str
    unique_visitors: int
    total_conversations: int
    total_messages: int
    leads_generated: int
    conversion_rate: float
    avg_messages_per_conversation: float
    avg_response_latency_ms: float
    token_usage_total: int
    estimated_cost_usd: float
