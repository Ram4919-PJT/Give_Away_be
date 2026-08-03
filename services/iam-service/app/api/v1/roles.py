from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.role_service import RoleService
from app.db.session import get_db
from app.dependencies.auth import get_current_user, require_roles
from app.models.enums import RoleName
from app.models.user import User
from app.schemas.role import RoleResponse

router = APIRouter(prefix="/roles", tags=["Roles"])


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    _user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await RoleService(db).list_roles()


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: UUID,
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await RoleService(db).get_role(role_id)
