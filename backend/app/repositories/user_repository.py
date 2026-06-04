"""User repository — all SQL lives here."""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        return await self.session.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        full_name: str,
    ) -> User:
        user = User(email=email.lower(), password_hash=password_hash, full_name=full_name)
        self.session.add(user)
        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def mark_verified(self, user_id: UUID) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(is_verified=True)
        )
        await self.session.commit()

    async def update_password(self, user_id: UUID, password_hash: str) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(password_hash=password_hash)
        )
        await self.session.commit()

    async def touch_last_login(self, user_id: UUID) -> None:
        await self.session.execute(
            update(User).where(User.id == user_id).values(last_login=datetime.utcnow())
        )
        await self.session.commit()
