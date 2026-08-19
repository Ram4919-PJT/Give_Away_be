from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundError
from app.db.session import get_db
from app.dependencies.auth import require_roles
from app.models.enums import RoleName, UserStatus
from app.models.role import Role
from app.models.user import User
from app.schemas.user import RoleAssignRequest, UserStatusUpdate, UserUpdate, UserWithRoleResponse

router = APIRouter(prefix="/users", tags=["Users"])


def _normalize_status(value: str) -> str:
    normalized = value.strip().upper()
    allowed = {item.value for item in UserStatus}
    if normalized not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{value}'",
        )
    return normalized


@router.get("", response_model=list[UserWithRoleResponse])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    role: str | None = Query(None, description="Filter by role name, e.g. RECEIVER"),
    q: str | None = Query(None, min_length=1, max_length=100),
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(User).options(selectinload(User.role)).order_by(User.created_at.desc())
    if status_filter:
        stmt = stmt.where(User.status == _normalize_status(status_filter))
    if role:
        stmt = stmt.join(Role, User.role_id == Role.role_id).where(
            Role.role_name == role.strip().upper()
        )
    if q:
        keyword = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                User.full_name.ilike(keyword),
                User.email.ilike(keyword),
                User.mobile.ilike(keyword),
            )
        )
    result = await db.execute(stmt.offset(skip).limit(limit))
    return list(result.scalars().unique().all())


@router.get("/{user_id}", response_model=UserWithRoleResponse)
async def get_user(
    user_id: int,
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User #{user_id} not found")
    return user


@router.patch("/{user_id}", response_model=UserWithRoleResponse)
async def update_user(
    user_id: int,
    data: UserUpdate,
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.user_id == user_id)
    )
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
        user.status = _normalize_status(data.status)

    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/status", response_model=UserWithRoleResponse)
async def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User #{user_id} not found")

    user.status = _normalize_status(data.status)
    await db.commit()
    await db.refresh(user)
    return user


@router.patch("/{user_id}/role", response_model=UserWithRoleResponse)
async def assign_role(
    user_id: int,
    data: RoleAssignRequest,
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(User).options(selectinload(User.role)).where(User.user_id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise NotFoundError(f"User #{user_id} not found")

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
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.user_id == user_id))
    user = result.scalar_one_or_none()
    if user:
        await db.delete(user)
        await db.commit()
