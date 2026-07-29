from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import RoleName
from app.models.role import Role


class RoleRepository:
    """
    Repository responsible for all database operations related to Role.

    This class should only interact with the database and must not
    contain business logic.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session


    async def create(
        self,
        *,
        role_name: RoleName,
        description: str | None = None,
    ) -> Role:
        """
        Create a new role.
        """

        role = Role(
            role_name=role_name,
            description=description,
        )

        self.session.add(role)

        await self.session.flush()
        await self.session.refresh(role)

        return role

    async def get_by_id(
        self,
        role_id: uuid.UUID,
    ) -> Role | None:
        """
        Retrieve a role by its UUID.
        """

        stmt = select(Role).where(
            Role.role_id == role_id
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        role_name: RoleName,
    ) -> Role | None:
        """
        Retrieve a role using its enum name.
        """

        stmt = select(Role).where(
            Role.role_name == role_name
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none()

    async def list_all(self) -> list[Role]:
        """
        Retrieve all roles.
        """

        stmt = (
            select(Role)
            .order_by(Role.role_name)
        )

        result = await self.session.execute(stmt)

        return list(result.scalars().all())

    async def exists(
        self,
        role_name: RoleName,
    ) -> bool:
        """
        Check whether a role already exists.
        """

        stmt = select(Role.role_id).where(
            Role.role_name == role_name
        )

        result = await self.session.execute(stmt)

        return result.scalar_one_or_none() is not None


    async def update(
        self,
        role: Role,
        *,
        description: str | None = None,
    ) -> Role:
        """
        Update an existing role.
        """

        role.description = description

        await self.session.flush()
        await self.session.refresh(role)

        return role

    async def delete(
        self,
        role: Role,
    ) -> None:
        """
        Delete a role.
        """

        await self.session.delete(role)

        await self.session.flush()