from pydantic import BaseModel, Field

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core_app.db.session import get_db
from core_app.dependencies.auth import TokenUser
from core_app.dependencies.auth_optional import get_optional_user
from core_app.services import payment_service, razorpay_service

router = APIRouter(prefix="/donations", tags=["Payments"])


class CreateOrderRequest(BaseModel):
    amount: float = Field(..., gt=0)
    program_id: int = Field(..., gt=0)
    mobile: str | None = None
    donor_name: str | None = None
    currency: str = "INR"


class VerifyPaymentRequest(BaseModel):
    orderId: str = Field(..., min_length=3)
    paymentId: str = Field(..., min_length=3)
    signature: str = Field(..., min_length=3)


@router.post("/create-order")
async def create_donation_order(
    body: CreateOrderRequest,
    db: AsyncSession = Depends(get_db),
    user: TokenUser | None = Depends(get_optional_user),
):
    try:
        user_id = user.user_id if user and user.role == "DONOR" else None
        mobile = body.mobile if not user_id else None
        return await payment_service.create_payment_order(
            db,
            user_id=user_id,
            mobile=mobile,
            donor_name=body.donor_name,
            program_id=body.program_id,
            amount=body.amount,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/verify-payment")
async def verify_donation_payment(
    body: VerifyPaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await payment_service.verify_and_confirm_payment(
            db,
            order_id=body.orderId,
            payment_id=body.paymentId,
            signature=body.signature,
        )
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("/receipt/{donation_id}")
async def get_donation_receipt(
    donation_id: int,
    db: AsyncSession = Depends(get_db),
):
    try:
        return await payment_service.get_donation_receipt(db, donation_id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/webhook/razorpay")
async def razorpay_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature", "")
    if not razorpay_service.verify_webhook_signature(body, signature):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid webhook signature")

    payload = await request.json()
    event = payload.get("event", "")
    entity = payload.get("payload", {}).get("payment", {}).get("entity", {})
    if event == "payment.captured":
        order_id = entity.get("order_id")
        payment_id = entity.get("id")
        if order_id and payment_id:
            try:
                await payment_service.confirm_payment_from_webhook(
                    db,
                    order_id=order_id,
                    payment_id=payment_id,
                )
            except (LookupError, ValueError):
                pass
    return {"success": True}
