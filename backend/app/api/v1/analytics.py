"""Analytics: summary, events, export."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentPrincipal, DbSession
from app.repositories.chatbot_repository import AnalyticsRepository
from app.schemas.resources import AnalyticsSummaryOut

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _period_to_since(period: str) -> datetime:
    days = {"7d": 7, "30d": 30, "90d": 90}.get(period, 30)
    return datetime.utcnow() - timedelta(days=days)


@router.get("/summary")
async def summary(
    principal: CurrentPrincipal,
    session: DbSession,
    chatbot_id: str | None = Query(default=None),
    period: str = Query("30d"),
):
    repo = AnalyticsRepository(session)
    cid = None
    if chatbot_id:
        from uuid import UUID

        cid = UUID(chatbot_id)
    metrics = await repo.summary(principal.workspace_id, cid, _period_to_since(period))
    return {"data": AnalyticsSummaryOut(period=period, **metrics).model_dump()}


@router.get("/events")
async def events(
    principal: CurrentPrincipal,
    session: DbSession,
    chatbot_id: str | None = Query(default=None),
    event_type: str | None = Query(default=None),
    from_: str | None = Query(default=None, alias="from"),
    to: str | None = Query(default=None),
):
    from uuid import UUID

    repo = AnalyticsRepository(session)
    cid = UUID(chatbot_id) if chatbot_id else None
    start = datetime.fromisoformat(from_) if from_ else datetime.utcnow() - timedelta(days=7)
    end = datetime.fromisoformat(to) if to else datetime.utcnow()
    items = await repo.query_events(principal.workspace_id, cid, event_type, start, end)
    return {
        "data": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "session_id": str(e.session_id),
                "page_url": e.page_url,
                "data": e.data,
                "created_at": e.created_at.isoformat(),
            }
            for e in items
        ]
    }


@router.get("/export")
async def export_events(
    principal: CurrentPrincipal,
    session: DbSession,
    chatbot_id: str | None = Query(default=None),
    format: str = Query("csv", pattern="^(csv|json)$"),
):
    from uuid import UUID

    repo = AnalyticsRepository(session)
    cid = UUID(chatbot_id) if chatbot_id else None
    start = datetime.utcnow() - timedelta(days=30)
    end = datetime.utcnow()
    items = await repo.query_events(principal.workspace_id, cid, None, start, end, limit=100_000)
    if format == "json":
        return {"data": [e.__dict__ for e in items]}
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "event_type", "session_id", "page_url", "created_at"])
    for e in items:
        writer.writerow([e.id, e.event_type, e.session_id, e.page_url, e.created_at.isoformat()])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=analytics.csv"},
    )
