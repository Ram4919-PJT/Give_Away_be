from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.models.applications import ApplicationStatusHistory, AssistanceApplication, NgoFundRequest, NgoItemRequest

router = APIRouter(prefix="/applications", tags=["Assistance Applications"])


class ApplicationCreate(BaseModel):
    receiver_id: int
    purpose: str
    amount_requested: float


class ReviewAppRequest(BaseModel):
    status: str  # APPROVED, REJECTED, UNDER_REVIEW


@router.get("")
async def list_applications(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AssistanceApplication))
    return result.scalars().all()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_application(data: ApplicationCreate, db: AsyncSession = Depends(get_db)):
    app = AssistanceApplication(
        receiver_id=data.receiver_id,
        purpose=data.purpose,
        amount_requested=data.amount_requested,
        status="SUBMITTED",
    )
    db.add(app)
    await db.commit()
    await db.refresh(app)
    
    hist = ApplicationStatusHistory(application_id=app.application_id, status="SUBMITTED")
    db.add(hist)
    await db.commit()
    return app


@router.post("/{application_id}/review")
async def review_application(
    application_id: int,
    action: ReviewAppRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AssistanceApplication).where(AssistanceApplication.application_id == application_id))
    app = result.scalar_one_or_none()
    if not app:
        raise HTTPException(status_code=404, detail=f"Application #{application_id} not found")

    new_status = action.status.upper()
    app.status = new_status
    
    hist = ApplicationStatusHistory(application_id=application_id, status=new_status)
    db.add(hist)
    
    await db.commit()
    return {"message": f"Application #{application_id} updated to {new_status}", "status": new_status}


@router.get("/ngo-item-requests")
async def list_ngo_item_requests(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NgoItemRequest))
    return result.scalars().all()


@router.post("/ngo-item-requests/{request_id}/review")
async def review_ngo_item_request(
    request_id: int,
    action: ReviewAppRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(NgoItemRequest).where(NgoItemRequest.request_id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail=f"NGO item request #{request_id} not found")

    req.status = action.status.upper()
    await db.commit()
    return {"message": f"NGO item request #{request_id} updated to {req.status}", "status": req.status}


@router.get("/ngo-fund-requests")
async def list_ngo_fund_requests(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(NgoFundRequest))
    return result.scalars().all()


@router.post("/ngo-fund-requests/{request_id}/review")
async def review_ngo_fund_request(
    request_id: int,
    action: ReviewAppRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(NgoFundRequest).where(NgoFundRequest.request_id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail=f"NGO fund request #{request_id} not found")

    req.status = action.status.upper()
    await db.commit()
    return {"message": f"NGO fund request #{request_id} updated to {req.status}", "status": req.status}
