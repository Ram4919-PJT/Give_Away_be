from uuid import UUID

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.otp_service import OtpService
from app.db.session import get_db
from app.schemas.otp import OtpSendRequest, OtpVerifyRequest

router = APIRouter(prefix="/otp", tags=["OTP"])


@router.post("/send", status_code=status.HTTP_204_NO_CONTENT)
async def send_otp(data: OtpSendRequest, db: AsyncSession = Depends(get_db)):
    await OtpService(db).send_otp(data)


@router.post("/verify", status_code=status.HTTP_204_NO_CONTENT)
async def verify_otp(data: OtpVerifyRequest, db: AsyncSession = Depends(get_db)):
    await OtpService(db).verify_otp(data)
