from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies.auth import require_roles
from app.models.enums import RoleName
from app.models.user import User
from app.repositories.login_audit_repository import LoginAuditRepository
from app.schemas.login_audit import LoginAuditResponse

router = APIRouter(prefix="/audit", tags=["Login Audit"])


@router.get("/logins", response_model=list[LoginAuditResponse])
async def list_login_audits(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await LoginAuditRepository(db).list_all(skip=skip, limit=limit)


@router.get("/logins/user/{user_id}", response_model=list[LoginAuditResponse])
async def list_user_login_audits(
    user_id: UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    _admin: User = Depends(require_roles(RoleName.SUPER_ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    return await LoginAuditRepository(db).get_user_login_history(
        user_id, skip=skip, limit=limit
    )
