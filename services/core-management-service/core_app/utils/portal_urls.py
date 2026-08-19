"""Build absolute URLs for user app vs admin portal notifications."""

from core_app.config import settings


def user_app_url(path: str) -> str:
    if not path:
        return settings.USER_APP_URL.rstrip("/")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = settings.USER_APP_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def admin_portal_url(path: str = "/") -> str:
    if not path:
        return settings.ADMIN_PORTAL_URL.rstrip("/")
    if path.startswith("http://") or path.startswith("https://"):
        return path
    base = settings.ADMIN_PORTAL_URL.rstrip("/")
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{base}{path}"


def admin_kyc_review_url(*, request_id: int, request_type: str) -> str:
    type_key = (request_type or "").upper()
    if type_key == "NGO":
        return admin_portal_url(f"/?tab=kyc-ngo&requestId={request_id}")
    if type_key == "RECEIVER":
        return admin_portal_url(f"/?tab=kyc-receiver&requestId={request_id}")
    if type_key == "DONOR":
        return admin_portal_url(f"/?tab=kyc-donor&requestId={request_id}")
    return admin_portal_url(f"/?tab=verification&requestId={request_id}")


def admin_assistance_review_url(*, application_id: int | None = None) -> str:
    if application_id:
        return admin_portal_url(f"/?tab=assistance&applicationId={application_id}")
    return admin_portal_url("/?tab=assistance")


def admin_item_verification_url(*, item_donation_id: int | None = None) -> str:
    if item_donation_id:
        return admin_portal_url(f"/?tab=items&itemId={item_donation_id}")
    return admin_portal_url("/?tab=items")
