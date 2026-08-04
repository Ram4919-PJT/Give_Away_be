from enum import Enum


class RoleName(str, Enum):
    """System roles."""

    DONOR = "DONOR"
    RECEIVER = "RECEIVER"
    NGO = "NGO"
    SUPER_ADMIN = "SUPER_ADMIN"


class UserStatus(str, Enum):
    """User account status."""

    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    SUSPENDED = "SUSPENDED"


class LoginAuditStatus(str, Enum):
    """Login attempt result."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class OtpPurpose(str, Enum):
    """OTP usage purpose."""

    REGISTRATION = "REGISTRATION"
    LOGIN = "LOGIN"
    PASSWORD_RESET = "PASSWORD_RESET"
    MOBILE_VERIFICATION = "MOBILE_VERIFICATION"


class OtpVerificationStatus(str, Enum):
    """OTP verification state."""

    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    EXPIRED = "EXPIRED"


class TokenType(str, Enum):
    """JWT token types."""

    ACCESS = "ACCESS"
    REFRESH = "REFRESH"