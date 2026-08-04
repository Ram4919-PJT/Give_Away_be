from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.models.role import Role
from app.repositories.role_repository import RoleRepository


class RoleService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.role_repo = RoleRepository(db)

    async def list_roles(self) -> list[Role]:
        return await self.role_repo.list_all()

    async def get_role(self, role_id: UUID) -> Role:
        role = await self.role_repo.get_by_id(role_id)
        if not role:
            raise NotFoundError("Role not found")
        return role
