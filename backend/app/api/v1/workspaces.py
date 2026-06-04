"""Workspace + website routers."""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends

from app.core.dependencies import CurrentPrincipal, DbSession
from app.schemas.resources import (
    WebsiteCreate,
    WebsiteUpdate,
    WorkspaceCreate,
    WorkspaceUpdate,
)
from app.services.workspace_service import WebsiteService, WorkspaceService

workspaces = APIRouter(prefix="/workspaces", tags=["Workspaces"])
websites = APIRouter(prefix="/websites", tags=["Websites"])


@workspaces.get("")
async def list_workspaces(
    principal: CurrentPrincipal,
    service: WorkspaceService = Depends(),
):
    items = await service.list_for_user(principal.user_id)
    return {"data": [w.__dict__ for w in items]}


@workspaces.post("", status_code=201)
async def create_workspace(
    payload: WorkspaceCreate,
    principal: CurrentPrincipal,
    service: WorkspaceService = Depends(),
):
    ws = await service.create(principal.user_id, payload)
    return {"data": {"id": str(ws.id), "subdomain": ws.subdomain}}


@workspaces.get("/{workspace_id}")
async def get_workspace(workspace_id: UUID, service: WorkspaceService = Depends()):
    ws = await service.get(workspace_id)
    return {"data": {"id": str(ws.id), "name": ws.name, "subdomain": ws.subdomain, "plan": ws.plan}}


@workspaces.put("/{workspace_id}")
async def update_workspace(
    workspace_id: UUID, payload: WorkspaceUpdate, service: WorkspaceService = Depends()
):
    ws = await service.update(workspace_id, payload)
    return {"data": {"id": str(ws.id), "name": ws.name, "settings": ws.settings}}


@websites.get("")
async def list_websites(
    principal: CurrentPrincipal, service: WebsiteService = Depends()
):
    items = await service.list_for_workspace(principal.workspace_id)
    return {"data": [w.__dict__ for w in items]}


@websites.post("", status_code=201)
async def create_website(
    payload: WebsiteCreate,
    principal: CurrentPrincipal,
    service: WebsiteService = Depends(),
):
    site = await service.create(principal.workspace_id, payload)
    return {"data": {"id": str(site.id), "url": site.url, "crawl_status": site.crawl_status.value}}


@websites.get("/{website_id}")
async def get_website(
    website_id: UUID,
    principal: CurrentPrincipal,
    service: WebsiteService = Depends(),
):
    site = await service.get(principal.workspace_id, website_id)
    return {"data": site.__dict__}


@websites.put("/{website_id}")
async def update_website(
    website_id: UUID,
    payload: WebsiteUpdate,
    principal: CurrentPrincipal,
    service: WebsiteService = Depends(),
):
    site = await service.update(principal.workspace_id, website_id, payload)
    return {"data": {"id": str(site.id), "name": site.name}}


@websites.delete("/{website_id}", status_code=204)
async def delete_website(
    website_id: UUID,
    principal: CurrentPrincipal,
    service: WebsiteService = Depends(),
):
    await service.delete(principal.workspace_id, website_id)
