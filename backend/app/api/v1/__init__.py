"""Aggregate v1 router — includes every domain router under /api/v1."""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import auth, session, workspaces
from app.api.v1 import crawl as crawl_router
from app.api.v1 import chatbots as chatbots_router
from app.api.v1 import chat as chat_router
from app.api.v1 import conversations as conversations_router
from app.api.v1 import leads as leads_router
from app.api.v1 import analytics as analytics_router
from app.api.v1 import billing as billing_router
from app.api.v1 import widget as widget_router

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(session.router)
api_router.include_router(workspaces.workspaces)
api_router.include_router(workspaces.websites)
api_router.include_router(crawl_router.router)
api_router.include_router(chatbots_router.router)
api_router.include_router(chat_router.router)
api_router.include_router(conversations_router.router)
api_router.include_router(leads_router.router)
api_router.include_router(analytics_router.router)
api_router.include_router(billing_router.router)
api_router.include_router(widget_router.router)
