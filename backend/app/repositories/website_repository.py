"""Website + page + chunk repository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.website import Chunk, CrawledPage, CrawlStatus, PageStatus, Website


class WebsiteRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_workspace(self, workspace_id: UUID) -> list[Website]:
        stmt = (
            select(Website)
            .where(Website.workspace_id == workspace_id, Website.is_deleted.is_(False))
            .order_by(Website.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get(self, workspace_id: UUID, website_id: UUID) -> Website | None:
        result = await self.session.execute(
            select(Website).where(
                Website.id == website_id,
                Website.workspace_id == workspace_id,
                Website.is_deleted.is_(False),
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(self, website_id: UUID) -> Website | None:
        return await self.session.get(Website, website_id)

    async def create(
        self,
        *,
        workspace_id: UUID,
        url: str,
        name: str,
        crawl_config: dict | None = None,
    ) -> Website:
        site = Website(
            workspace_id=workspace_id,
            url=url,
            name=name,
            crawl_config=crawl_config or {},
        )
        self.session.add(site)
        await self.session.commit()
        await self.session.refresh(site)
        return site

    async def update(self, website: Website, values: dict) -> Website:
        for k, v in values.items():
            if v is not None:
                setattr(website, k, v)
        await self.session.commit()
        await self.session.refresh(website)
        return website

    async def set_status(self, website_id: UUID, status: CrawlStatus, task_id: str | None = None) -> None:
        values: dict = {"crawl_status": status}
        if task_id is not None:
            values["celery_task_id"] = task_id
        await self.session.execute(update(Website).where(Website.id == website_id).values(**values))
        await self.session.commit()

    async def soft_delete(self, website_id: UUID) -> None:
        await self.session.execute(
            update(Website)
            .where(Website.id == website_id)
            .values(is_deleted=True)
        )
        await self.session.commit()

    async def count_for_workspace(self, workspace_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(Website.id)).where(
                Website.workspace_id == workspace_id, Website.is_deleted.is_(False)
            )
        )
        return int(result.scalar_one())


class PageRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, page: dict) -> CrawledPage:
        stmt = (
            pg_insert(CrawledPage)
            .values(**page)
            .on_conflict_do_update(
                index_elements=[CrawledPage.website_id, CrawledPage.canonical_url],
                set_={
                    "title": page.get("title"),
                    "meta_description": page.get("meta_description"),
                    "headings": page.get("headings", {}),
                    "content": page.get("content"),
                    "word_count": page.get("word_count", 0),
                    "language": page.get("language"),
                    "crawl_status": page.get("crawl_status", PageStatus.DONE),
                    "http_status": page.get("http_status"),
                    "redirect_chain": page.get("redirect_chain", []),
                    "crawled_at": page.get("crawled_at"),
                    "error_message": page.get("error_message"),
                },
            )
            .returning(CrawledPage)
        )
        result = await self.session.execute(stmt)
        await self.session.commit()
        return result.scalar_one()

    async def list_for_website(self, website_id: UUID) -> list[CrawledPage]:
        result = await self.session.execute(
            select(CrawledPage).where(CrawledPage.website_id == website_id)
        )
        return list(result.scalars().all())

    async def count_status(self, website_id: UUID) -> dict[str, int]:
        result = await self.session.execute(
            select(CrawledPage.crawl_status, func.count(CrawledPage.id))
            .where(CrawledPage.website_id == website_id)
            .group_by(CrawledPage.crawl_status)
        )
        return {str(status): count for status, count in result.all()}

    async def delete_for_website(self, website_id: UUID) -> None:
        await self.session.execute(
            delete(CrawledPage).where(CrawledPage.website_id == website_id)
        )
        await self.session.commit()


class ChunkRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def bulk_insert(self, chunks: list[dict]) -> None:
        if not chunks:
            return
        self.session.add_all([Chunk(**c) for c in chunks])
        await self.session.commit()

    async def delete_for_website(self, website_id: UUID) -> None:
        await self.session.execute(delete(Chunk).where(Chunk.website_id == website_id))
        await self.session.commit()

    async def count_for_workspace(self, workspace_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(Chunk.id)).where(Chunk.workspace_id == workspace_id)
        )
        return int(result.scalar_one())

    async def count_for_website(self, website_id: UUID) -> int:
        result = await self.session.execute(
            select(func.count(Chunk.id)).where(Chunk.website_id == website_id)
        )
        return int(result.scalar_one())
