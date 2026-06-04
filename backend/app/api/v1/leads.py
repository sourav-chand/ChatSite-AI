"""Leads list / get / delete / CSV export."""
from __future__ import annotations

import csv
import io
from uuid import UUID

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from app.core.dependencies import CurrentPrincipal, DbSession
from app.core.exceptions import NotFoundError
from app.repositories.chatbot_repository import LeadRepository
from app.schemas.common import PageMeta

router = APIRouter(prefix="/leads", tags=["Leads"])


@router.get("")
async def list_leads(
    principal: CurrentPrincipal,
    session: DbSession,
    chatbot_id: str = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
):
    repo = LeadRepository(session)
    items, total = await repo.list_for_chatbot(principal.workspace_id, UUID(chatbot_id), page, page_size)
    return {
        "data": [
            {
                "id": str(l.id),
                "email": l.email,
                "name": l.name,
                "phone": l.phone,
                "company": l.company,
                "source_page_url": l.source_page_url,
                "captured_at": l.captured_at.isoformat(),
            }
            for l in items
        ],
        "meta": PageMeta(page=page, page_size=page_size, total=total).model_dump(),
    }


@router.get("/{lead_id}")
async def get_lead(lead_id: UUID, principal: CurrentPrincipal, session: DbSession):
    lead = await LeadRepository(session).get(principal.workspace_id, lead_id)
    if not lead:
        raise NotFoundError("Lead not found")
    return {"data": lead.__dict__}


@router.delete("/{lead_id}", status_code=204)
async def delete_lead(lead_id: UUID, principal: CurrentPrincipal, session: DbSession):
    lead = await LeadRepository(session).get(principal.workspace_id, lead_id)
    if not lead:
        raise NotFoundError("Lead not found")
    await LeadRepository(session).delete(lead)


@router.get("/export")
async def export_leads(
    principal: CurrentPrincipal,
    session: DbSession,
    chatbot_id: str = Query(...),
    format: str = Query("csv", pattern="^(csv|json)$"),
):
    repo = LeadRepository(session)
    items, _ = await repo.list_for_chatbot(principal.workspace_id, UUID(chatbot_id), 1, 10_000)
    if format == "json":
        return {"data": [l.__dict__ for l in items]}
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "name", "email", "phone", "company", "source_page_url", "captured_at"])
    for l in items:
        writer.writerow([l.id, l.name, l.email, l.phone, l.company, l.source_page_url, l.captured_at.isoformat()])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=leads.csv"},
    )
