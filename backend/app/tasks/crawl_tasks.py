"""Crawl / embed / reindex Celery tasks."""
from __future__ import annotations

import asyncio
from datetime import datetime
from uuid import UUID

import structlog
from celery import chord, group
from sqlalchemy import select, update

from app.chunking.strategies import ChunkingService
from app.core.config import settings
from app.crawler.async_crawler import AsyncCrawler, PageResult
from app.database.session import AsyncSessionLocal
from app.embeddings.openai_embeddings import EmbeddingService
from app.models.website import Chunk, CrawledPage, CrawlStatus, PageStatus, Website
from app.qdrant.client import QdrantService
from app.repositories.website_repository import ChunkRepository, PageRepository, WebsiteRepository
from app.tasks.celery_app import celery_app

log = structlog.get_logger(__name__)


def _run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if not asyncio.get_event_loop().is_running() else asyncio.run(coro)


async def _crawl_website_async(website_id: UUID) -> list[dict]:
    async with AsyncSessionLocal() as session:
        repo = WebsiteRepository(session)
        site = await repo.get_by_id(website_id)
        if not site:
            return []
        await repo.set_status(website_id, CrawlStatus.RUNNING)

        crawler = AsyncCrawler(
            site.url,
            max_depth=int(site.crawl_config.get("max_depth", settings.CRAWL_MAX_DEPTH)),
            concurrency=int(site.crawl_config.get("concurrency", settings.CRAWL_CONCURRENCY)),
        )
        results = await crawler.crawl()

        page_repo = PageRepository(session)
        saved: list[CrawledPage] = []
        for r in results:
            page_dict = {
                "website_id": website_id,
                "workspace_id": site.workspace_id,
                "url": r.url,
                "canonical_url": r.canonical_url,
                "title": r.title,
                "meta_description": r.meta_description,
                "headings": r.headings,
                "content": r.main_content,
                "word_count": r.word_count,
                "content_hash": r.content_hash,
                "language": r.language,
                "crawl_status": PageStatus.DONE if not r.error else PageStatus.FAILED,
                "http_status": r.http_status,
                "redirect_chain": r.redirect_chain,
                "crawled_at": datetime.utcnow(),
                "error_message": r.error,
            }
            page = await page_repo.upsert(page_dict)
            saved.append(page)

        await session.execute(
            update(Website)
            .where(Website.id == website_id)
            .values(pages_count=len(saved), last_crawled_at=datetime.utcnow())
        )
        await repo.set_status(website_id, CrawlStatus.DONE)
        return [
            {
                "id": str(p.id),
                "url": p.canonical_url,
                "title": p.title,
                "content": p.content or "",
                "workspace_id": str(p.workspace_id),
                "website_id": str(p.website_id),
            }
            for p in saved
            if p.crawl_status == PageStatus.DONE and p.content
        ]


@celery_app.task(name="app.tasks.crawl_tasks.crawl_website_task", bind=True, max_retries=2)
def crawl_website_task(self, website_id: str) -> dict:
    """Orchestrator: crawl → enqueue embed_chunks_task."""
    try:
        pages = _run(_crawl_website_async(UUID(website_id)))
        if pages:
            embed_chunks_task.delay(pages)
        return {"website_id": website_id, "pages": len(pages)}
    except Exception as exc:
        log.exception("crawl_website_task.failed", website_id=website_id, error=str(exc))
        _run(_mark_failed(website_id))
        raise self.retry(exc=exc, countdown=60)


async def _mark_failed(website_id: str) -> None:
    async with AsyncSessionLocal() as session:
        repo = WebsiteRepository(session)
        await repo.set_status(UUID(website_id), CrawlStatus.FAILED)


@celery_app.task(name="app.tasks.crawl_tasks.crawl_page_task", bind=True, max_retries=3)
def crawl_page_task(self, page_id: str, url: str) -> dict:
    """Individual page fetch with retry; used in chord by orchestrator."""
    return {"page_id": page_id, "url": url}


async def _embed_pages_async(pages: list[dict]) -> None:
    embedder = EmbeddingService()
    chunker = ChunkingService(
        strategy=settings.CHUNKING_STRATEGY,
        chunk_size=settings.CHUNK_SIZE,
        overlap=settings.CHUNK_OVERLAP,
    )
    qdrant = QdrantService()

    for page in pages:
        page_id = UUID(page["id"])
        website_id = UUID(page["website_id"])
        workspace_id = UUID(page["workspace_id"])
        chunks = await chunker.split(page["content"])
        records = chunker.to_db_records(
            chunks,
            page_id=page_id,
            website_id=website_id,
            workspace_id=workspace_id,
            embedding_model=settings.OPENAI_MODEL_EMBED,
        )
        if not records:
            continue
        vectors = await embedder.embed([r["content"] for r in records])

        async with AsyncSessionLocal() as session:
            chunk_repo = ChunkRepository(session)
            await chunk_repo.bulk_insert(records)
            await session.execute(
                update(Website).where(Website.id == website_id).values(chunks_count=Website.chunks_count + len(records))
            )

        for r, v in zip(records, vectors):
            r["vector"] = v
            r["source_url"] = page["url"]
            r["title"] = page["title"]
        await qdrant.upsert_chunks(workspace_id, records)


@celery_app.task(name="app.tasks.crawl_tasks.embed_chunks_task", bind=True, max_retries=2)
def embed_chunks_task(self, pages: list[dict]) -> dict:
    try:
        _run(_embed_pages_async(pages))
        return {"embedded_pages": len(pages)}
    except Exception as exc:
        log.exception("embed_chunks_task.failed", error=str(exc))
        raise self.retry(exc=exc, countdown=30)


async def _reindex_async(website_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        site = await session.get(Website, website_id)
        if not site:
            return
        chunk_repo = ChunkRepository(session)
        page_repo = PageRepository(session)
        await chunk_repo.delete_for_website(website_id)
        await page_repo.delete_for_website(website_id)


@celery_app.task(name="app.tasks.crawl_tasks.reindex_website_task", bind=True, max_retries=2)
def reindex_website_task(self, website_id: str) -> dict:
    try:
        _run(_reindex_async(UUID(website_id)))
        crawl_website_task.delay(website_id)
        return {"website_id": website_id, "status": "reindex_started"}
    except Exception as exc:
        raise self.retry(exc=exc, countdown=30)
