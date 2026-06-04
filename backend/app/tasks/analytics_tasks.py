"""Analytics rollup + scheduled crawl dispatch."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import func, select

from app.database.session import AsyncSessionLocal
from app.models.analytics import AnalyticsDaily, AnalyticsEvent
from app.models.chatbot import Chatbot
from app.models.website import CrawlStatus, Website
from app.repositories.analytics_repository import AnalyticsRepository
from app.tasks.celery_app import celery_app
from app.tasks.crawl_tasks import crawl_website_task

log = structlog.get_logger(__name__)


async def _rollup_day(day: date) -> None:
    async with AsyncSessionLocal() as session:
        start = datetime.combine(day, datetime.min.time())
        end = start + timedelta(days=1)

        rows = await session.execute(
            select(
                AnalyticsEvent.workspace_id,
                AnalyticsEvent.chatbot_id,
                AnalyticsEvent.event_type,
                func.count(AnalyticsEvent.id),
                func.count(func.distinct(AnalyticsEvent.session_id)),
            )
            .where(AnalyticsEvent.created_at >= start, AnalyticsEvent.created_at < end)
            .group_by(
                AnalyticsEvent.workspace_id,
                AnalyticsEvent.chatbot_id,
                AnalyticsEvent.event_type,
            )
        )

        agg: dict[tuple[UUID, UUID], dict] = {}
        for ws_id, bot_id, ev_type, count, uniq in rows.all():
            bucket = agg.setdefault((ws_id, bot_id), {})
            if ev_type == "page_view":
                bucket["unique_visitors"] = uniq
                bucket["page_views"] = count
            elif ev_type == "conversation_start":
                bucket["conversations"] = count
            elif ev_type == "message_sent":
                bucket["messages"] = count
            elif ev_type == "lead_captured":
                bucket["leads"] = count

        repo = AnalyticsRepository(session)
        for (ws_id, bot_id), metrics in agg.items():
            convs = metrics.get("conversations", 0)
            leads = metrics.get("leads", 0)
            metrics["conversion_rate"] = round((leads / convs * 100) if convs else 0.0, 2)
            await repo.upsert_daily(workspace_id=ws_id, chatbot_id=bot_id, day=day, metrics=metrics)


@celery_app.task(name="app.tasks.analytics_tasks.analytics_daily_rollup_task")
def analytics_daily_rollup_task() -> dict:
    yesterday = date.today() - timedelta(days=1)
    try:
        asyncio.run(_rollup_day(yesterday))
        return {"rolled_up": yesterday.isoformat()}
    except Exception as exc:
        log.exception("analytics_daily_rollup.failed", error=str(exc))
        raise


@celery_app.task(name="app.tasks.schedule_tasks.scheduled_crawl_dispatch")
def scheduled_crawl_dispatch() -> dict:
    """Find websites due for a scheduled crawl and dispatch."""
    async def _run() -> list[str]:
        dispatched: list[str] = []
        async with AsyncSessionLocal() as session:
            now = datetime.utcnow()
            sites = (
                await session.execute(
                    select(Website).where(Website.crawl_status == CrawlStatus.IDLE)
                )
            ).scalars().all()
            for s in sites:
                cfg = s.crawl_config or {}
                schedule = cfg.get("schedule")
                if not schedule:
                    continue
                last = s.last_crawled_at or s.created_at
                interval_h = {"daily": 24, "weekly": 168}.get(schedule, 0)
                if interval_h and (now - last).total_seconds() >= interval_h * 3600:
                    crawl_website_task.delay(str(s.id))
                    dispatched.append(str(s.id))
        return dispatched

    return {"dispatched": asyncio.run(_run())}
