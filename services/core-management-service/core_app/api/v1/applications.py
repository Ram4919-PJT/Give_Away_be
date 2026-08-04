from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.core.exceptions import NotFoundError
from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser, get_current_user, require_roles
from core_app.schemas.applications import AssistanceRequestCreate, AssistanceRequestResponse
from core_app.services import core_service

router = APIRouter(prefix="/assistance", tags=["Core - Assistance"])


@router.get("/requests", response_model=list[AssistanceRequestResponse])
async def list_assistance_requests(
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.list_assistance_requests(db, user)


@router.get("/requests/{request_id}", response_model=AssistanceRequestResponse)
async def get_assistance_request(
    request_id: UUID,
    user: TokenUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    request = await core_service.get_assistance_request(db, user, request_id)
    if not request:
        raise NotFoundError("Assistance request not found")
    return request


@router.post("/requests", response_model=AssistanceRequestResponse, status_code=201)
async def create_assistance_request(
    payload: AssistanceRequestCreate,
    user: TokenUser = Depends(require_roles("RECEIVER")),
    db: AsyncSession = Depends(get_db),
):
    return await core_service.create_assistance_request(db, user, payload)
