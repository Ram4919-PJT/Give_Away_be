"""Central notification event types and template routing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EventEmailConfig:
    template_key: str
    subject: str
    preference_category: str  # account | donation | application | campaign
    force_send: bool = False  # security-critical emails bypass preferences


# Only events backed by real application flows.
EVENT_EMAIL_CONFIG: dict[str, EventEmailConfig] = {
    "ACCOUNT_CREATED": EventEmailConfig("welcome", "Welcome to Give Away", "account", force_send=True),
    "PASSWORD_RESET": EventEmailConfig("password_reset", "Your Give Away password reset code", "account", force_send=True),
    "PASSWORD_CHANGED": EventEmailConfig("password_changed", "Your Give Away password was changed", "account", force_send=True),
    "SECURITY_ALERT": EventEmailConfig("security_alert", "Security alert for your Give Away account", "account", force_send=True),
    "ACCOUNT_DEACTIVATED": EventEmailConfig("account_deactivated", "Your Give Away account was deactivated", "account", force_send=True),
    "DONATION_SUBMITTED": EventEmailConfig("donation_submitted", "Donation submitted — Give Away", "donation"),
    "PAYMENT_SUCCESS": EventEmailConfig("payment_success", "Payment successful — Give Away", "donation"),
    "PAYMENT_FAILED": EventEmailConfig("payment_failed", "Payment could not be completed — Give Away", "donation"),
    "ITEM_DONATION_SUBMITTED": EventEmailConfig("item_donation_submitted", "Item donation submitted — Give Away", "donation"),
    "ITEM_DONATION_APPROVED": EventEmailConfig("item_donation_approved", "Item donation approved — Give Away", "donation"),
    "ITEM_DONATION_REJECTED": EventEmailConfig("item_donation_rejected", "Item donation update — Give Away", "donation"),
    "PROFILE_VERIFICATION_SUBMITTED": EventEmailConfig("verification_submitted", "Verification submitted — Give Away", "account"),
    "PROFILE_VERIFIED": EventEmailConfig("profile_verified", "Your profile is verified — Give Away", "account"),
    "PROFILE_REJECTED": EventEmailConfig("profile_rejected", "Verification update — Give Away", "account"),
    "FUND_REQUEST_SUBMITTED": EventEmailConfig("fund_request_submitted", "Assistance request submitted — Give Away", "application"),
    "FUND_REQUEST_APPROVED": EventEmailConfig("fund_request_approved", "Assistance request approved — Give Away", "application"),
    "FUND_REQUEST_REJECTED": EventEmailConfig("fund_request_rejected", "Assistance request update — Give Away", "application"),
    "FUND_REQUEST_FULFILLED": EventEmailConfig("fund_request_fulfilled", "Assistance disbursed — Give Away", "application"),
    "NGO_VERIFICATION_SUBMITTED": EventEmailConfig("ngo_verification_submitted", "NGO verification submitted — Give Away", "account"),
    "NGO_VERIFIED": EventEmailConfig("ngo_verified", "Your NGO is verified — Give Away", "account"),
    "NGO_REJECTED": EventEmailConfig("ngo_rejected", "NGO verification update — Give Away", "account"),
    "CAMPAIGN_CREATED": EventEmailConfig("campaign_created", "Campaign created — Give Away", "campaign"),
    "GENERIC_NOTIFICATION": EventEmailConfig("generic", "Notification from Give Away", "account"),
}


NOTIFICATION_TYPE_TO_CATEGORY = {
    "DONATION": "donation",
    "APPLICATION": "application",
    "CAMPAIGN": "campaign",
    "ACCOUNT": "account",
    "SYSTEM": "account",
}
