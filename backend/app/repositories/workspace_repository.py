"""Workspace + membership repository."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.workspace import Workspace, WorkspaceMember, WorkspaceRole


class WorkspaceRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, workspace_id: UUID) -> Workspace | None:
        return await self.session.get(Workspace, workspace_id)

    async def list_for_user(self, user_id: UUID) -> list[Workspace]:
        stmt = (
            select(Workspace)
            .join(WorkspaceMember, WorkspaceMember.workspace_id == Workspace.id)
            .where(WorkspaceMember.user_id == user_id, Workspace.is_deleted.is_(False))
            .order_by(Workspace.created_at.desc())
        )
        return list((await self.session.execute(stmt)).scalars().all())

    async def get_by_subdomain(self, subdomain: str) -> Workspace | None:
        result = await self.session.execute(
            select(Workspace).where(Workspace.subdomain == subdomain.lower())
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        owner_id: UUID,
        name: str,
        subdomain: str,
        plan: str = "free",
        settings: dict | None = None,
    ) -> Workspace:
        ws = Workspace(
            owner_id=owner_id,
            name=name,
            subdomain=subdomain.lower(),
            plan=plan,
            settings=settings or {},
        )
        self.session.add(ws)
        await self.session.flush()
        self.session.add(
            WorkspaceMember(workspace_id=ws.id, user_id=owner_id, role=WorkspaceRole.OWNER)
        )
        await self.session.commit()
        await self.session.refresh(ws)
        return ws

    async def update(self, workspace_id: UUID, values: dict) -> Workspace | None:
        ws = await self.session.get(Workspace, workspace_id)
        if not ws:
            return None
        for key, val in values.items():
            if val is not None:
                setattr(ws, key, val)
        await self.session.commit()
        await self.session.refresh(ws)
        return ws

    async def member_role(self, workspace_id: UUID, user_id: UUID) -> WorkspaceRole | None:
        result = await self.session.execute(
            select(WorkspaceMember.role).where(
                WorkspaceMember.workspace_id == workspace_id,
                WorkspaceMember.user_id == user_id,
            )
        )
        return result.scalar_one_or_none()
