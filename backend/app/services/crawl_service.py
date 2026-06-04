"""Crawl service — thin facade over Celery tasks + status aggregator."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from celery.result import AsyncResult

from app.database.session import AsyncSessionLocal
from app.models.website import CrawlStatus, PageStatus, Website
from app.repositories.website_repository import PageRepository, WebsiteRepository
from app.tasks.celery_app import celery_app
from app.tasks.crawl_tasks import crawl_website_task, reindex_website_task


class CrawlService:
    @staticmethod
    async def start(workspace_id: UUID, website_id: UUID, force_recrawl: bool) -> dict:
        async with AsyncSessionLocal() as session:
            repo = WebsiteRepository(session)
            site = await repo.get(workspace_id, website_id)
            if not site:
                return {"error": "not_found"}
            if site.crawl_status == CrawlStatus.RUNNING:
                return {"status": "already_running"}
            if force_recrawl:
                page_repo = PageRepository(session)
                chunk_repo = __import__("app.repositories.website_repository", fromlist=["ChunkRepository"]).ChunkRepository(session)
                await chunk_repo.delete_for_website(site.id)
                await page_repo.delete_for_website(site.id)
            task = crawl_website_task.delay(str(site.id))
            await repo.set_status(site.id, CrawlStatus.RUNNING, task_id=task.id)
        return {"status": "started", "task_id": task.id}

    @staticmethod
    async def stop(workspace_id: UUID, website_id: UUID) -> dict:
        async with AsyncSessionLocal() as session:
            repo = WebsiteRepository(session)
            site = await repo.get(workspace_id, website_id)
            if not site:
                return {"error": "not_found"}
            if site.celery_task_id:
                celery_app.control.revoke(site.celery_task_id, terminate=True)
            await repo.set_status(site.id, CrawlStatus.PAUSED)
        return {"status": "paused"}

    @staticmethod
    async def reindex(workspace_id: UUID, website_id: UUID) -> dict:
        async with AsyncSessionLocal() as session:
            repo = WebsiteRepository(session)
            site = await repo.get(workspace_id, website_id)
            if not site:
                return {"error": "not_found"}
            task = reindex_website_task.delay(str(site.id))
            await repo.set_status(site.id, CrawlStatus.RUNNING, task_id=task.id)
        return {"status": "reindex_started", "task_id": task.id}

    @staticmethod
    async def status(workspace_id: UUID, website_id: str) -> dict:
        async with AsyncSessionLocal() as session:
            repo = WebsiteRepository(session)
            site = await repo.get_by_id(UUID(website_id))
            if not site or site.workspace_id != workspace_id:
                return {"error": "not_found"}
            counts = await PageRepository(session).count_status(site.id)
            celery_state = None
            if site.celery_task_id:
                celery_state = AsyncResult(site.celery_task_id).state
        return {
            "website_id": str(site.id),
            "status": site.crawl_status.value,
            "pages_found": site.pages_count,
            "pages_crawled": counts.get("done", 0),
            "pages_failed": counts.get("failed", 0),
            "chunks_embedded": site.chunks_count,
            "celery_state": celery_state,
            "last_crawled_at": site.last_crawled_at.isoformat() if site.last_crawled_at else None,
        }
