"""Platform configuration endpoints (read-only, non-sensitive)."""

from fastapi import APIRouter

from core_app.schemas.donor_verification_config import DonorVerificationConfigOut
from core_app.schemas.receiver_assistance_config import ReceiverAssistanceConfigOut
from core_app.schemas.receiver_kyc_config import ReceiverKycConfigOut
from core_app.services.kyc.donor_document_config import build_donor_verification_config_response
from core_app.services.kyc.receiver_document_config import build_receiver_kyc_config_response
from core_app.services.receiver_assistance_config import build_receiver_assistance_config_response

router = APIRouter(prefix="/config", tags=["Configuration"])


@router.get("/receiver-assistance", response_model=ReceiverAssistanceConfigOut)
async def get_receiver_assistance_config() -> dict:
    """Canonical Receiver financial assistance categories and document requirements."""
    return build_receiver_assistance_config_response()


@router.get("/receiver-kyc", response_model=ReceiverKycConfigOut)
async def get_receiver_kyc_config() -> dict:
    """Receiver KYC purposes, document requirements, and wizard metadata."""
    return build_receiver_kyc_config_response()


@router.get("/donor-verification", response_model=DonorVerificationConfigOut)
async def get_donor_verification_config() -> dict:
    """Donor verification document requirements and upload limits."""
    return build_donor_verification_config_response()
