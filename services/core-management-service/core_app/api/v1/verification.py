from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, get_current_user, require_roles
from core_app.schemas.donations import VerificationRequestCreate, VerificationRequestResponse
from core_app.services import core_service

router = APIRouter(prefix="/verification", tags=["Core - Verification"])


@router.get("/requests", response_model=list[VerificationRequestResponse])
async def list_verification_requests(
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.list_verification_requests(db, user)


@router.post("/requests", response_model=VerificationRequestResponse, status_code=201)
async def create_verification_request(
    payload: VerificationRequestCreate,
    user: TokenUser = Depends(require_roles("DONOR", "RECEIVER", "NGO")),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.create_verification_request(db, user, payload)
