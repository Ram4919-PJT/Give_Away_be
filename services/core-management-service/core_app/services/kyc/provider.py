"""KYC provider abstraction — plug in authorized providers via configuration."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from core_app.config import settings


@dataclass
class IdentityVerificationResult:
    verified: bool
    provider: str
    reference: str | None = None
    document_type: str | None = None
    verified_at: datetime | None = None
    message: str | None = None
    metadata: dict[str, Any] | None = None


class KycProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    async def verify_identity(
        self,
        *,
        document_type: str,
        document_number: str,
        full_name: str | None = None,
        dob: str | None = None,
    ) -> IdentityVerificationResult:
        raise NotImplementedError


class ManualKycProvider(KycProvider):
    @property
    def name(self) -> str:
        return "MANUAL"

    async def verify_identity(
        self,
        *,
        document_type: str,
        document_number: str,
        full_name: str | None = None,
        dob: str | None = None,
    ) -> IdentityVerificationResult:
        return IdentityVerificationResult(
            verified=False,
            provider=self.name,
            document_type=document_type,
            message="Submitted for manual review",
            metadata={"mode": "manual_review"},
        )


class MockKycProvider(KycProvider):
    @property
    def name(self) -> str:
        return "MOCK_DEV"

    async def verify_identity(
        self,
        *,
        document_type: str,
        document_number: str,
        full_name: str | None = None,
        dob: str | None = None,
    ) -> IdentityVerificationResult:
        if settings.ENV == "production" or not settings.ALLOW_MOCK_KYC:
            raise PermissionError("Mock KYC is disabled")
        return IdentityVerificationResult(
            verified=True,
            provider=self.name,
            reference=f"MOCK-{document_type}-{datetime.now(UTC).strftime('%Y%m%d%H%M%S')}",
            document_type=document_type,
            verified_at=datetime.now(UTC).replace(tzinfo=None),
            message="DEVELOPMENT VERIFICATION — not real KYC",
            metadata={"development": True},
        )


def get_kyc_provider() -> KycProvider:
    provider = (settings.KYC_PROVIDER or "MANUAL").upper()
    if provider == "MOCK":
        return MockKycProvider()
    return ManualKycProvider()
