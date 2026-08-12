from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.models.verification import RejectionReason, VerificationDocument, VerificationRequest, VerificationStatusHistory
from core_app.models.profiles import NgoProfile, ReceiverProfile

router = APIRouter(prefix="/verification", tags=["Verification"])


class ReviewActionRequest(BaseModel):
    status: str  # "VERIFIED" or "REJECTED"
    reason: str | None = None


@router.get("/requests")
async def list_verification_requests(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VerificationRequest))
    requests = result.scalars().all()
    
    response = []
    for req in requests:
        doc_res = await db.execute(select(VerificationDocument).where(VerificationDocument.request_id == req.request_id))
        docs = doc_res.scalars().all()
        
        reason_res = await db.execute(select(RejectionReason).where(RejectionReason.request_id == req.request_id))
        reasons = reason_res.scalars().all()
        
        response.append({
            "request_id": req.request_id,
            "user_id": req.user_id,
            "request_type": req.request_type,
            "status": req.status,
            "submitted_at": req.submitted_at,
            "documents": [{"document_id": d.document_id, "document_type": d.document_type, "file_url": d.file_url, "uploaded_at": d.uploaded_at} for d in docs],
            "rejection_reasons": [{"reason_id": r.reason_id, "reason": r.reason, "created_at": r.created_at} for r in reasons],
        })
    return response


@router.get("/requests/{request_id}")
async def get_verification_request(request_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VerificationRequest).where(VerificationRequest.request_id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail=f"Verification request #{request_id} not found")
        
    doc_res = await db.execute(select(VerificationDocument).where(VerificationDocument.request_id == req.request_id))
    docs = doc_res.scalars().all()
    
    reason_res = await db.execute(select(RejectionReason).where(RejectionReason.request_id == req.request_id))
    reasons = reason_res.scalars().all()
    
    return {
        "request_id": req.request_id,
        "user_id": req.user_id,
        "request_type": req.request_type,
        "status": req.status,
        "submitted_at": req.submitted_at,
        "documents": [{"document_id": d.document_id, "document_type": d.document_type, "file_url": d.file_url, "uploaded_at": d.uploaded_at} for d in docs],
        "rejection_reasons": [{"reason_id": r.reason_id, "reason": r.reason, "created_at": r.created_at} for r in reasons],
    }


@router.post("/requests/{request_id}/review")
async def review_verification_request(
    request_id: int,
    action: ReviewActionRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(VerificationRequest).where(VerificationRequest.request_id == request_id))
    req = result.scalar_one_or_none()
    if not req:
        raise HTTPException(status_code=404, detail=f"Verification request #{request_id} not found")

    new_status = action.status.upper()
    req.status = new_status
    
    # Record status history
    history = VerificationStatusHistory(request_id=request_id, status=new_status)
    db.add(history)

    # If rejected and reason provided, store rejection reason
    if new_status == "REJECTED" and action.reason:
        rej = RejectionReason(request_id=request_id, reason=action.reason)
        db.add(rej)

    # Update profile status if matching profile exists
    if req.request_type == "RECEIVER":
        rec_res = await db.execute(select(ReceiverProfile).where(ReceiverProfile.user_id == req.user_id))
        rec_prof = rec_res.scalar_one_or_none()
        if rec_prof:
            rec_prof.verification_status = new_status
    elif req.request_type == "NGO":
        ngo_res = await db.execute(select(NgoProfile).where(NgoProfile.user_id == req.user_id))
        ngo_prof = ngo_res.scalar_one_or_none()
        if ngo_prof:
            ngo_prof.verification_status = new_status

    await db.commit()
    return {"message": f"Verification request #{request_id} updated to {new_status}", "request_id": request_id, "status": new_status}


@router.get("/documents")
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(VerificationDocument))
    return result.scalars().all()


@router.get("/rejection-reasons")
async def list_rejection_reasons(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(RejectionReason))
    return result.scalars().all()
