"""Crawl control router."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentPrincipal
from app.schemas.resources import CrawlStartIn, CrawlStatusOut, CrawlStopIn
from app.services.crawl_service import CrawlService

router = APIRouter(prefix="/crawl", tags=["Crawl"])


@router.post("/start", status_code=202)
async def start_crawl(payload: CrawlStartIn, principal: CurrentPrincipal, _: bool = Depends(lambda: True)):
    return await CrawlService.start(principal.workspace_id, payload.website_id, payload.force_recrawl)


@router.post("/stop", status_code=202)
async def stop_crawl(payload: CrawlStopIn, principal: CurrentPrincipal):
    return await CrawlService.stop(principal.workspace_id, payload.website_id)


@router.post("/reindex", status_code=202)
async def reindex(payload: CrawlStopIn, principal: CurrentPrincipal):
    return await CrawlService.reindex(principal.workspace_id, payload.website_id)


@router.get("/status/{website_id}")
async def status(website_id: str, principal: CurrentPrincipal):
    return await CrawlService.status(principal.workspace_id, website_id)
