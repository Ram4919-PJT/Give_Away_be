"""Professional HTML email templates for Give Away."""

from __future__ import annotations

import html
from typing import Any


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value))


def _base_layout(*, title: str, greeting: str, body_html: str, cta_label: str | None, cta_url: str | None) -> str:
    cta_block = ""
    if cta_label and cta_url:
        cta_block = f"""
        <tr><td style="padding:24px 0 8px;text-align:center;">
          <a href="{_esc(cta_url)}" style="display:inline-block;background:#1268E8;color:#FFFFFF;text-decoration:none;font-weight:600;font-size:14px;padding:12px 22px;border-radius:10px;">{_esc(cta_label)}</a>
        </td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{_esc(title)}</title>
</head>
<body style="margin:0;padding:0;background:#F8FAFC;font-family:Inter,Arial,sans-serif;color:#0F172A;">
  <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#F8FAFC;padding:24px 12px;">
    <tr><td align="center">
      <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#FFFFFF;border:1px solid #E5E7EB;border-radius:16px;overflow:hidden;">
        <tr><td style="padding:24px 28px 12px;text-align:center;background:linear-gradient(180deg,#EFF6FF 0%,#FFFFFF 100%);">
          <div style="font-size:22px;font-weight:800;color:#1268E8;letter-spacing:-0.02em;">Give Away</div>
          <div style="font-size:12px;color:#64748B;margin-top:4px;">Serve • Support • Uplift</div>
        </td></tr>
        <tr><td style="padding:8px 28px 0;font-size:16px;font-weight:700;">{_esc(greeting)}</td></tr>
        <tr><td style="padding:12px 28px 0;font-size:14px;line-height:1.6;color:#475569;">{body_html}</td></tr>
        {cta_block}
        <tr><td style="padding:20px 28px 24px;font-size:12px;line-height:1.5;color:#94A3B8;border-top:1px solid #F1F5F9;">
          Give Away · AJA Abayahastham<br />
          This is an automated notification. Please do not reply to this email.<br />
          Need help? Contact support through the Give Away portal.
        </td></tr>
      </table>
    </td></tr>
  </table>
</body>
</html>"""


def _info_card(rows: list[tuple[str, str]]) -> str:
    items = "".join(
        f'<tr><td style="padding:8px 0;color:#64748B;font-size:13px;width:40%;">{_esc(k)}</td>'
        f'<td style="padding:8px 0;color:#0F172A;font-size:13px;font-weight:600;">{_esc(v)}</td></tr>'
        for k, v in rows
        if v
    )
    return f"""
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin-top:16px;background:#F8FAFC;border:1px solid #E5E7EB;border-radius:12px;">
      <tr><td style="padding:14px 16px;">{items}</td></tr>
    </table>"""


def render_email_template(template_key: str, context: dict[str, Any]) -> tuple[str, str]:
    """Return (subject_suffix, html_body). Subject prefix may be overridden by caller."""
    name = context.get("user_name") or context.get("recipient_name") or "there"
    greeting = f"Hello {name},"
    cta_url = context.get("action_url") or context.get("cta_url")
    cta_label = context.get("cta_label") or "Open Give Away"

    if template_key == "welcome":
        body = (
            "<p>Welcome to <strong>Give Away</strong>. Your account has been created successfully.</p>"
            "<p>You can now sign in to explore ways to give, receive support, and coordinate relief through AJA Abayahastham.</p>"
        )
        return "Welcome to Give Away", _base_layout(title="Welcome", greeting=greeting, body_html=body, cta_label="Go to Dashboard", cta_url=cta_url or "/dashboard")

    if template_key == "password_reset":
        otp = context.get("otp_code") or context.get("otp")
        body = (
            "<p>We received a request to reset your Give Away password.</p>"
            f"{_info_card([('Verification code', otp), ('Expires in', context.get('expires_in', '10 minutes'))])}"
            "<p style='margin-top:12px;font-size:13px;color:#64748B;'>If you did not request this, you can safely ignore this email.</p>"
        )
        return "Password reset code", _base_layout(title="Password Reset", greeting=greeting, body_html=body, cta_label=None, cta_url=None)

    if template_key == "password_changed":
        body = "<p>Your Give Away account password was changed successfully.</p><p>If this wasn't you, contact support immediately.</p>"
        return "Password changed", _base_layout(title="Password Changed", greeting=greeting, body_html=body, cta_label="Review Security", cta_url=cta_url or "/dashboard")

    if template_key == "account_deactivated":
        body = "<p>Your Give Away account has been deactivated as requested.</p><p>Contact support if you need to reactivate your account.</p>"
        return "Account deactivated", _base_layout(title="Account Deactivated", greeting=greeting, body_html=body, cta_label=None, cta_url=None)

    if template_key == "security_alert":
        body = f"<p>{_esc(context.get('message', 'A security-related change was made on your account.'))}</p>"
        return "Security alert", _base_layout(title="Security Alert", greeting=greeting, body_html=body, cta_label="Review Account", cta_url=cta_url or "/dashboard")

    if template_key == "payment_success":
        body = (
            "<p>Your payment was successful. Thank you for your contribution.</p>"
            f"{_info_card([
                ('Campaign', context.get('campaign_name') or context.get('program_name')),
                ('Amount', context.get('amount_display') or context.get('amount')),
                ('Reference', context.get('donation_id') or context.get('reference_id')),
                ('Status', context.get('status', 'CONFIRMED')),
                ('Date', context.get('date')),
            ])}"
        )
        return "Payment successful", _base_layout(title="Payment Successful", greeting=greeting, body_html=body, cta_label="View Donation", cta_url=cta_url)

    if template_key == "payment_failed":
        body = (
            "<p>We could not complete your payment.</p>"
            f"{_info_card([
                ('Amount', context.get('amount_display') or context.get('amount')),
                ('Reference', context.get('donation_id') or context.get('reference_id')),
                ('Reason', context.get('reason') or context.get('message')),
            ])}"
            "<p>You can try again from your Give Away dashboard.</p>"
        )
        return "Payment failed", _base_layout(title="Payment Failed", greeting=greeting, body_html=body, cta_label="Try Again", cta_url=cta_url)

    if template_key in {"donation_submitted", "item_donation_submitted"}:
        body = (
            f"<p>{_esc(context.get('message', 'Your donation has been submitted and is being processed.'))}</p>"
            f"{_info_card([
                ('Type', context.get('donation_type') or context.get('item_name')),
                ('Amount / Qty', context.get('amount_display') or context.get('quantity')),
                ('Reference', context.get('donation_id') or context.get('request_id')),
                ('Status', context.get('status', 'SUBMITTED')),
            ])}"
        )
        return "Donation submitted", _base_layout(title="Donation Submitted", greeting=greeting, body_html=body, cta_label="View Details", cta_url=cta_url)

    if template_key in {"item_donation_approved", "item_donation_rejected"}:
        status = "approved" if "approved" in template_key else "updated"
        body = (
            f"<p>Your item donation has been <strong>{status}</strong>.</p>"
            f"{_info_card([
                ('Item', context.get('item_name') or context.get('category')),
                ('Status', context.get('status')),
                ('Reference', context.get('donation_id')),
                ('Notes', context.get('rejection_reason') or context.get('message')),
            ])}"
        )
        return f"Item donation {status}", _base_layout(title="Item Donation Update", greeting=greeting, body_html=body, cta_label="View Donation", cta_url=cta_url)

    if template_key in {"verification_submitted", "ngo_verification_submitted"}:
        body = "<p>Your verification documents have been submitted successfully.</p><p>Our team will review them and notify you once the review is complete.</p>"
        return "Verification submitted", _base_layout(title="Verification Submitted", greeting=greeting, body_html=body, cta_label="View Status", cta_url=cta_url)

    if template_key in {"profile_verified", "ngo_verified"}:
        body = "<p>Great news — your organization/profile verification is complete.</p><p>You now have access to the features unlocked by verification.</p>"
        return "Verification approved", _base_layout(title="Verified", greeting=greeting, body_html=body, cta_label="Open Dashboard", cta_url=cta_url or "/dashboard")

    if template_key in {"profile_rejected", "ngo_rejected"}:
        body = (
            "<p>Your verification could not be approved at this time.</p>"
            f"{_info_card([('Reason', context.get('rejection_reason') or context.get('message'))])}"
            "<p>Please review the requirements and submit updated documents if needed.</p>"
        )
        return "Verification update", _base_layout(title="Verification Update", greeting=greeting, body_html=body, cta_label="Review Verification", cta_url=cta_url)

    if template_key == "fund_request_submitted":
        body = (
            "<p>Your financial assistance request has been received.</p>"
            f"{_info_card([
                ('Request ID', context.get('request_id') or context.get('application_id')),
                ('Amount', context.get('amount_display') or context.get('amount')),
                ('Status', context.get('status', 'SUBMITTED')),
            ])}"
        )
        return "Request submitted", _base_layout(title="Request Submitted", greeting=greeting, body_html=body, cta_label="Track Request", cta_url=cta_url)

    if template_key == "fund_request_approved":
        body = (
            "<p>Your financial assistance request has been <strong>approved</strong>.</p>"
            f"{_info_card([
                ('Request ID', context.get('request_id') or context.get('application_id')),
                ('Approved amount', context.get('amount_approved') or context.get('amount_display')),
                ('Status', context.get('status', 'APPROVED')),
            ])}"
        )
        return "Request approved", _base_layout(title="Request Approved", greeting=greeting, body_html=body, cta_label="View Request", cta_url=cta_url)

    if template_key == "fund_request_rejected":
        body = (
            "<p>Your financial assistance request was not approved.</p>"
            f"{_info_card([
                ('Request ID', context.get('request_id') or context.get('application_id')),
                ('Status', context.get('status', 'REJECTED')),
                ('Reason', context.get('rejection_reason') or context.get('message')),
            ])}"
        )
        return "Request update", _base_layout(title="Request Update", greeting=greeting, body_html=body, cta_label="View Request", cta_url=cta_url)

    if template_key == "fund_request_fulfilled":
        body = (
            "<p>Your approved assistance has been disbursed.</p>"
            f"{_info_card([
                ('Request ID', context.get('request_id') or context.get('application_id')),
                ('Amount', context.get('amount_display') or context.get('amount')),
                ('Status', context.get('status', 'FULFILLED')),
            ])}"
        )
        return "Assistance disbursed", _base_layout(title="Assistance Disbursed", greeting=greeting, body_html=body, cta_label="View Request", cta_url=cta_url)

    if template_key == "campaign_created":
        body = (
            "<p>Your campaign has been created successfully.</p>"
            f"{_info_card([
                ('Campaign', context.get('campaign_name') or context.get('program_name')),
                ('Goal', context.get('goal_display') or context.get('goal_amount')),
                ('Status', context.get('status', 'ACTIVE')),
            ])}"
        )
        return "Campaign created", _base_layout(title="Campaign Created", greeting=greeting, body_html=body, cta_label="View Campaign", cta_url=cta_url)

    # generic fallback
    message = context.get("message") or context.get("body") or "You have a new update on Give Away."
    title = context.get("title") or "Notification"
    body = f"<p>{_esc(message)}</p>"
    if context.get("details"):
        body += _info_card(list(context["details"].items()) if isinstance(context["details"], dict) else [])
    return title, _base_layout(title=title, greeting=greeting, body_html=body, cta_label=cta_label, cta_url=cta_url)
