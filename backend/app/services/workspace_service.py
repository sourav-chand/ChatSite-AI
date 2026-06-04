"""Workspace + website business logic."""
from __future__ import annotations

from typing import Annotated
from uuid import UUID

import re
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import DbSession
from app.core.exceptions import ConflictError, NotFoundError, ValidationFailedError
from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole
from app.repositories.workspace_repository import WorkspaceRepository
from app.repositories.website_repository import WebsiteRepository
from app.schemas.resources import (
    WebsiteCreate,
    WebsiteUpdate,
    WorkspaceCreate,
    WorkspaceUpdate,
)

SUBDOMAIN_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,61}[a-z0-9])$")


class WorkspaceService:
    def __init__(self, session: Annotated[AsyncSession, Depends(DbSession)]) -> None:
        self.session = session
        self.repo = WorkspaceRepository(session)

    async def list_for_user(self, user_id: UUID) -> list[Workspace]:
        return await self.repo.list_for_user(user_id)

    async def get(self, workspace_id: UUID) -> Workspace:
        ws = await self.repo.get(workspace_id)
        if not ws:
            raise NotFoundError("Workspace not found")
        return ws

    async def create(self, owner_id: UUID, payload: WorkspaceCreate) -> Workspace:
        if not SUBDOMAIN_RE.match(payload.subdomain.lower()):
            raise ValidationFailedError("Invalid subdomain")
        if await self.repo.get_by_subdomain(payload.subdomain):
            raise ConflictError("Subdomain already in use")
        return await self.repo.create(
            owner_id=owner_id,
            name=payload.name,
            subdomain=payload.subdomain,
            plan=payload.plan,
        )

    async def update(self, workspace_id: UUID, payload: WorkspaceUpdate) -> Workspace:
        ws = await self.repo.update(workspace_id, payload.model_dump(exclude_none=True))
        if not ws:
            raise NotFoundError("Workspace not found")
        return ws

    async def add_member(self, workspace_id: UUID, user_id: UUID, role: WorkspaceRole) -> None:
        existing = await self.repo.member_role(workspace_id, user_id)
        if existing:
            raise ConflictError("User already a member")
        self.session.add(WorkspaceMember(workspace_id=workspace_id, user_id=user_id, role=role))
        await self.session.commit()


class WebsiteService:
    def __init__(self, session: Annotated[AsyncSession, Depends(DbSession)]) -> None:
        self.session = session
        self.repo = WebsiteRepository(session)

    async def list_for_workspace(self, workspace_id: UUID) -> list:
        return await self.repo.list_for_workspace(workspace_id)

    async def get(self, workspace_id: UUID, website_id: UUID):
        site = await self.repo.get(workspace_id, website_id)
        if not site:
            raise NotFoundError("Website not found")
        return site

    async def create(self, workspace_id: UUID, payload: WebsiteCreate):
        from app.tasks.crawl_tasks import crawl_website_task

        site = await self.repo.create(
            workspace_id=workspace_id,
            url=str(payload.url),
            name=payload.name,
            crawl_config=payload.crawl_config,
        )
        task = crawl_website_task.delay(str(site.id))
        await self.repo.set_status(site.id, __import__("app.models.website", fromlist=["CrawlStatus"]).CrawlStatus.RUNNING, task_id=task.id)
        return site

    async def update(self, workspace_id: UUID, website_id: UUID, payload: WebsiteUpdate):
        site = await self.get(workspace_id, website_id)
        return await self.repo.update(site, payload.model_dump(exclude_none=True))

    async def delete(self, workspace_id: UUID, website_id: UUID) -> None:
        site = await self.get(workspace_id, website_id)
        await self.repo.soft_delete(site.id)
