import re
from ipaddress import ip_address
from pydantic import EmailStr

FULL_NAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z\s'.-]{1,254}$")
MOBILE_PATTERN = re.compile(r"^[6-9]\d{9}$")          # India 10-digit
OTP_PATTERN = re.compile(r"^\d{4,6}$")
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*(),.?\":{}|<>]).{8,128}$"
)


def normalize_email(value: EmailStr | str) -> str:
    return str(value).strip().lower()


def normalize_full_name(value: str) -> str:
    cleaned = " ".join(value.strip().split())
    if len(cleaned) < 2:
        raise ValueError("Full name must be at least 2 characters")
    if not FULL_NAME_PATTERN.match(cleaned):
        raise ValueError("Full name contains invalid characters")
    return cleaned


def normalize_mobile(value: str) -> str:
    digits = re.sub(r"\D", "", value.strip())

    if digits.startswith("91") and len(digits) == 12:
        digits = digits[2:]

    if not MOBILE_PATTERN.match(digits):
        raise ValueError("Mobile must be a valid 10-digit Indian number")

    return digits


def validate_password(value: str) -> str:
    if not PASSWORD_PATTERN.match(value):
        raise ValueError(
            "Password must be 8-128 chars with upper, lower, digit, and special character"
        )
    return value


def validate_otp_code(value: str) -> str:
    code = value.strip()
    if not OTP_PATTERN.match(code):
        raise ValueError("OTP must be 4 to 6 digits")
    return code


def validate_ip_address(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    ip_address(cleaned)  # raises ValueError if invalid
    return cleaned