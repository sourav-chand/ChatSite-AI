"""Aggregate SQLAlchemy models for Alembic discovery."""
from __future__ import annotations

from app.models.analytics import AnalyticsDaily, AnalyticsEvent
from app.models.billing import APIKey, AuditLog, Subscription
from app.models.chatbot import Chatbot, Conversation, Lead, Message
from app.models.user import User
from app.models.website import Chunk, CrawledPage, Website
from app.models.workspace import Workspace, WorkspaceMember

__all__ = [
    "APIKey",
    "AnalyticsDaily",
    "AnalyticsEvent",
    "AuditLog",
    "Chatbot",
    "Chunk",
    "Conversation",
    "CrawledPage",
    "Lead",
    "Message",
    "Subscription",
    "User",
    "Website",
    "Workspace",
    "WorkspaceMember",
]
