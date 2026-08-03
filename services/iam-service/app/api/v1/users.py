from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.user_service import UserService
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.user import RoleAssignRequest, UserStatusUpdate, UserUpdate, UserWithRoleResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserWithRoleResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await UserService(db).list_users(skip=skip, limit=limit)


@router.get("/{user_id}", response_model=UserWithRoleResponse)
async def get_user(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.user_id != user_id and current_user.role.role_name != RoleName.SUPER_ADMIN:
        from app.core.exceptions import AuthorizationError

        raise AuthorizationError("Cannot view this user")
    return await UserService(db).get_user(user_id)


@router.patch("/{user_id}", response_model=UserWithRoleResponse)
async def update_user(
    user_id: UUID,
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_admin = current_user.role.role_name == RoleName.SUPER_ADMIN
    if current_user.user_id != user_id and not is_admin:
        from app.core.exceptions import AuthorizationError

        raise AuthorizationError("Cannot update this user")

    if not is_admin:
        data.status = None
        data.role_name = None

    return await UserService(db).update_user(user_id, data, is_admin=is_admin)


@router.patch("/{user_id}/status", response_model=UserWithRoleResponse)
async def update_user_status(
    user_id: UUID,
    data: UserStatusUpdate,
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await UserService(db).update_status(user_id, data.status)


@router.patch("/{user_id}/role", response_model=UserWithRoleResponse)
async def assign_role(
    user_id: UUID,
    data: RoleAssignRequest,
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await UserService(db).assign_role(user_id, data.role_name)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: UUID,
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    await UserService(db).delete_user(user_id)
