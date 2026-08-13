from __future__ import annotations

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security.password import hash_password
from app.models.enums import UserStatus
from app.models.user import User
from app.schemas.auth import RegisterRequest


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, user: User) -> User:
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def create_from_register(self, data: RegisterRequest, role_id: int) -> User:
        user = User(
            role_id=role_id,
            full_name=data.full_name,
            email=str(data.email),
            mobile=data.mobile,
            password_hash=hash_password(data.password.get_secret_value()),
            status=UserStatus.PENDING,
        )
        return await self.create(user)


    async def get_by_id(self, user_id: int) -> User | None:
        stmt = (
            select(User)
            .options(
                selectinload(User.role),
            )
            .where(User.user_id == user_id)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(func.lower(User.email) == email.lower())
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_mobile(self, mobile: str) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(User.mobile == mobile)
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_email_or_mobile(
        self,
        identifier: str,
    ) -> User | None:
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(
                or_(
                    func.lower(User.email) == identifier.lower(),
                    User.mobile == identifier,
                )
            )
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
    ) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .offset(skip)
            .limit(limit)
            .order_by(User.created_at.desc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_status(
        self,
        status: UserStatus,
    ) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(User.status == status)
            .order_by(User.created_at.desc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_role(self, role_id: int) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(User.role_id == role_id)
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def search(self, keyword: str) -> list[User]:
        stmt = (
            select(User)
            .options(selectinload(User.role))
            .where(
                or_(
                    User.full_name.ilike(f"%{keyword}%"),
                    User.email.ilike(f"%{keyword}%"),
                    User.mobile.ilike(f"%{keyword}%"),
                )
            )
            .order_by(User.created_at.desc())
        )

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def exists_by_email(self, email: str) -> bool:
        stmt = select(User.user_id).where(
            func.lower(User.email) == email.lower()
        )

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def exists_by_mobile(self, mobile: str) -> bool:
        stmt = select(User.user_id).where(User.mobile == mobile)

        result = await self.session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def count(self) -> int:
        stmt = select(func.count(User.user_id))

        result = await self.session.execute(stmt)
        return result.scalar_one()


    async def update(self, user: User) -> User:
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def update_password(
        self,
        user: User,
        password_hash: str,
    ) -> User:
        user.password_hash = password_hash

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def update_status(
        self,
        user: User,
        status: UserStatus,
    ) -> User:
        user.status = status

        await self.session.flush()
        await self.session.refresh(user)

        return user

    async def update_role(
        self,
        user: User,
        role_id: int,
    ) -> User:
        user.role_id = role_id

        await self.session.flush()
        await self.session.refresh(user)

        return user


    async def delete(self, user: User) -> None:
        await self.session.delete(user)
        await self.session.flush()