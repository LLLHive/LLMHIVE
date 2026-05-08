"""Outbound transactional email helpers (Resend HTTP API).

Mirrors the frontend ``lib/email.ts`` pattern:

- If ``RESEND_API_KEY`` is unset the helper logs the intended send and returns
  ``{"sent": False, "skipped": True}``. This keeps dev/test environments from
  failing when no provider is configured.
- If ``RESEND_API_KEY`` is set we POST to ``https://api.resend.com/emails`` and
  return ``{"sent": True, "id": ...}`` on 200. Failures are logged but never
  raise to the caller (a webhook handler must not 5xx because email delivery
  failed).

The templates here are deliberately small and inline; richer marketing
templates live in the frontend (``lib/email.ts``). These exist so the backend
webhook can notify the user when something the backend learned about first
(payment failure, subscription deletion) needs an immediate email.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_RESEND_ENDPOINT = "https://api.resend.com/emails"
_DEFAULT_FROM = "LLMHive <noreply@contact.llmhive.ai>"
_DEFAULT_APP_URL = "https://llmhive.ai"
_HTTP_TIMEOUT_SECONDS = 5.0


def _api_key() -> Optional[str]:
    return os.getenv("RESEND_API_KEY") or None


def _from_address() -> str:
    return os.getenv("EMAIL_FROM") or _DEFAULT_FROM


def _app_url() -> str:
    return (
        os.getenv("LLMHIVE_APP_URL")
        or os.getenv("NEXT_PUBLIC_APP_URL")
        or _DEFAULT_APP_URL
    ).rstrip("/")


def _post_email(
    *,
    to: str,
    subject: str,
    html: str,
    text: str,
) -> Dict[str, Any]:
    api_key = _api_key()
    if not api_key:
        logger.info(
            "email.skipped: RESEND_API_KEY unset; would send to=%s subject=%r",
            to,
            subject,
        )
        return {"sent": False, "skipped": True, "reason": "no_api_key"}

    body = {
        "from": _from_address(),
        "to": to,
        "subject": subject,
        "html": html,
        "text": text,
    }

    try:
        response = httpx.post(
            _RESEND_ENDPOINT,
            json=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=_HTTP_TIMEOUT_SECONDS,
        )
    except Exception as exc:
        logger.warning("email.send_failed to=%s: %s", to, exc)
        return {"sent": False, "skipped": False, "error": str(exc)}

    if response.status_code >= 400:
        logger.warning(
            "email.send_failed to=%s status=%s body=%s",
            to,
            response.status_code,
            response.text[:300],
        )
        return {
            "sent": False,
            "skipped": False,
            "status_code": response.status_code,
            "error": response.text[:300],
        }

    try:
        payload = response.json()
        message_id = payload.get("id")
    except Exception:
        message_id = None
    logger.info("email.sent to=%s subject=%r id=%s", to, subject, message_id)
    return {"sent": True, "skipped": False, "id": message_id}


def send_payment_failed_email(
    *,
    to: str,
    customer_name: Optional[str] = None,
    invoice_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Notify the user that their renewal payment failed.

    Returns ``{"sent": bool, ...}``. Never raises — webhook handlers should
    keep returning 200 to Stripe even if the email send fails.
    """
    if not to:
        logger.warning("email.payment_failed: no recipient address")
        return {"sent": False, "skipped": True, "reason": "no_recipient"}

    first_name = (customer_name or "").split(" ")[0] or "there"
    app_url = _app_url()
    update_url = invoice_url or f"{app_url}/billing"

    subject = "Action required: your LLMHive payment failed"
    html = f"""<!DOCTYPE html>
<html><head><meta charset=\"utf-8\"><title>{subject}</title></head>
<body style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#0a0a0a;color:#e5e5e5;margin:0;padding:24px;\">
  <div style=\"max-width:560px;margin:0 auto;background:#171717;border:1px solid #262626;border-radius:12px;padding:32px;\">
    <h2 style=\"margin:0 0 16px 0;color:#f5f5f5;\">Hi {first_name},</h2>
    <p style=\"color:#a3a3a3;line-height:1.6;\">
      Your most recent LLMHive renewal payment did not go through. Your subscription has been
      marked <strong style=\"color:#f87171;\">past&nbsp;due</strong>, and paid features are temporarily
      paused until billing is restored.
    </p>
    <p style=\"color:#a3a3a3;line-height:1.6;\">
      Update your payment method to resume access right away:
    </p>
    <p style=\"text-align:center;margin:28px 0;\">
      <a href=\"{update_url}\" style=\"display:inline-block;background:linear-gradient(135deg,#C48E48,#A67C3D);color:#0a0a0a;padding:12px 24px;border-radius:8px;font-weight:600;text-decoration:none;\">Update payment method</a>
    </p>
    <p style=\"color:#737373;font-size:13px;line-height:1.5;\">
      If you've already updated your card, no further action is needed — Stripe will retry
      automatically and we'll restore access as soon as the charge succeeds. Questions? Reply
      to this email or contact us at info@llmhive.ai.
    </p>
  </div>
</body></html>
"""
    text = (
        f"Hi {first_name},\n\n"
        "Your most recent LLMHive renewal payment did not go through. Your subscription has\n"
        "been marked past_due and paid features are temporarily paused.\n\n"
        f"Update your payment method to resume access: {update_url}\n\n"
        "If you've already updated your card, no further action is needed.\n"
        "Questions? info@llmhive.ai\n"
    )

    return _post_email(to=to, subject=subject, html=html, text=text)


def send_subscription_cancelled_email(
    *,
    to: str,
    customer_name: Optional[str] = None,
    period_end_iso: Optional[str] = None,
) -> Dict[str, Any]:
    """Confirm a successful cancellation. Sent when ``customer.subscription.deleted`` arrives."""
    if not to:
        logger.warning("email.cancellation: no recipient address")
        return {"sent": False, "skipped": True, "reason": "no_recipient"}

    first_name = (customer_name or "").split(" ")[0] or "there"
    app_url = _app_url()
    period_phrase = (
        f" through {period_end_iso}" if period_end_iso else ""
    )

    subject = "Your LLMHive subscription has been cancelled"
    html = f"""<!DOCTYPE html>
<html><head><meta charset=\"utf-8\"><title>{subject}</title></head>
<body style=\"font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;background:#0a0a0a;color:#e5e5e5;margin:0;padding:24px;\">
  <div style=\"max-width:560px;margin:0 auto;background:#171717;border:1px solid #262626;border-radius:12px;padding:32px;\">
    <h2 style=\"margin:0 0 16px 0;color:#f5f5f5;\">Hi {first_name},</h2>
    <p style=\"color:#a3a3a3;line-height:1.6;\">
      We've cancelled your LLMHive subscription. You'll keep paid access{period_phrase}, and
      we won't bill you again unless you re-subscribe.
    </p>
    <p style=\"color:#a3a3a3;line-height:1.6;\">
      Changed your mind? Re-activate any time at <a href=\"{app_url}/pricing\" style=\"color:#C48E48;\">{app_url}/pricing</a>.
    </p>
    <p style=\"color:#737373;font-size:13px;line-height:1.5;\">
      If you have feedback on what we could do better, just reply to this email — we read every note.
    </p>
  </div>
</body></html>
"""
    text = (
        f"Hi {first_name},\n\n"
        f"We've cancelled your LLMHive subscription. You'll keep paid access{period_phrase}.\n"
        f"Re-activate any time: {app_url}/pricing\n\n"
        "Feedback? Just reply.\n"
    )
    return _post_email(to=to, subject=subject, html=html, text=text)
