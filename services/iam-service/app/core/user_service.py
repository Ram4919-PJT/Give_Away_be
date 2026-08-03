from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthorizationError, ConflictError, NotFoundError
from app.events.publishers import EventPublisher
from app.models.enums import RoleName, UserStatus
from app.models.user import User
from app.repositories.role_repository import RoleRepository
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserUpdate


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.user_repo = UserRepository(db)
        self.role_repo = RoleRepository(db)

    async def list_users(self, *, skip: int = 0, limit: int = 20) -> list[User]:
        return await self.user_repo.list(skip=skip, limit=limit)

    async def get_user(self, user_id: UUID) -> User:
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    async def update_user(
        self,
        user_id: UUID,
        data: UserUpdate,
        *,
        is_admin: bool = False,
    ) -> User:
        user = await self.get_user(user_id)

        if data.full_name is not None:
            user.full_name = data.full_name
        if data.email is not None:
            existing = await self.user_repo.get_by_email(str(data.email))
            if existing and existing.user_id != user_id:
                raise ConflictError("Email already in use")
            user.email = str(data.email)
        if data.mobile is not None:
            existing = await self.user_repo.get_by_mobile(data.mobile)
            if existing and existing.user_id != user_id:
                raise ConflictError("Mobile already in use")
            user.mobile = data.mobile

        if is_admin:
            if data.status is not None:
                user.status = data.status
            if data.role_name is not None:
                role = await self.role_repo.get_by_name(data.role_name)
                if not role:
                    raise NotFoundError("Role not found")
                user.role_id = role.role_id

        await self.user_repo.update(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update_status(self, user_id: UUID, status: UserStatus) -> User:
        user = await self.get_user(user_id)
        user.status = status
        await self.user_repo.update(user)
        await self.db.commit()
        await self.db.refresh(user)

        event = "user.activated" if status == UserStatus.ACTIVE else "user.deactivated"
        await EventPublisher.publish(event, {"user_id": str(user.user_id)})

        return user

    async def assign_role(self, user_id: UUID, role_name: RoleName) -> User:
        if role_name == RoleName.SUPER_ADMIN:
            raise AuthorizationError("Cannot assign SUPER_ADMIN via API")

        role = await self.role_repo.get_by_name(role_name)
        if not role:
            raise NotFoundError("Role not found")

        user = await self.get_user(user_id)
        user.role_id = role.role_id
        await self.user_repo.update(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def delete_user(self, user_id: UUID) -> None:
        user = await self.get_user(user_id)
        await self.user_repo.delete(user)
        await self.db.commit()
