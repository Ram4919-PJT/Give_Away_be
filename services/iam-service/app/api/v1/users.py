from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.models.user import User
from app.schemas.user import RoleAssignRequest, UserStatusUpdate, UserUpdate, UserWithRoleResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("", response_model=list[UserWithRoleResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).offset(skip).limit(limit))
    users = result.scalars().all()
    return users


@router.get("/{user_id}", response_model=UserWithRoleResponse)
async def get_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User #{user_id} not found")
    return user


@router.patch("/{user_id}", response_model=UserWithRoleResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User #{user_id} not found")

    if data.full_name is not None:
        user.full_name = data.full_name
    if data.email is not None:
        user.email = str(data.email)
    if data.mobile is not None:
        user.mobile = data.mobile
    if data.status is not None:
        user.status = data.status

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=UserWithRoleResponse)
async def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User #{user_id} not found")

    user.status = data.status
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserWithRoleResponse)
async def assign_role(
    user_id: int,
    data: RoleAssignRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User #{user_id} not found")

    from app.models.role import Role
    role_res = await db.execute(select(Role).where(Role.role_name == data.role_name))
    role = role_res.scalar_one_or_none()
    if not role:
        raise NotFoundError(f"Role '{data.role_name}' not found")

    user.role_id = role.role_id
    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        await db.commit()
