"""
Reminder delivery channel adapters.

Each channel implements the same `deliver()` interface. `in_app` is a no-op
(the bell surfaces due reminders). `email` is implemented (Phase 4). SMS and
WhatsApp land in Phases 5-6 and plug in the same way.
"""

import logging
import os
from typing import Optional

from services.email import send_email
from services.sms import send_sms
from services.whatsapp import send_whatsapp

logger = logging.getLogger(__name__)

KNOWN_CHANNELS = {"in_app", "email", "sms", "whatsapp"}


def _app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost").rstrip("/")


def _short_body(reminder: dict) -> str:
    """A concise message for SMS / WhatsApp, with a manage link for opt-out."""
    message = reminder.get("message", "")
    return f"VERA reminder: {message}\n\nManage or turn off: {_app_base_url()}/notifications"


async def _deliver_email(reminder: dict, contact: dict) -> bool:
    to = (contact or {}).get("email")
    if not to:
        logger.info("Email channel skipped for reminder %s: no verified email", reminder.get("id"))
        return False

    message = reminder.get("message", "")
    app = _app_base_url()
    manage = f"{app}/notifications"
    html = f"""\
<div style="font-family:Inter,Arial,sans-serif;color:#181c1e;max-width:520px;margin:0 auto;padding:8px;">
  <p style="color:#006480;font-weight:700;font-size:20px;margin:0 0 16px;">VERA</p>
  <p style="font-size:16px;line-height:1.6;margin:0 0 24px;">{message}</p>
  <p style="margin:0 0 24px;">
    <a href="{app}" style="background:#006480;color:#ffffff;padding:12px 22px;border-radius:9999px;text-decoration:none;font-weight:600;">Open VERA</a>
  </p>
  <hr style="border:none;border-top:1px solid #e0e3e5;margin:24px 0;">
  <p style="font-size:12px;color:#6f787d;line-height:1.5;">
    You are receiving this because you turned on email reminders in VERA.
    <a href="{manage}" style="color:#006480;">Manage or turn these off</a>.
  </p>
</div>"""
    text = f"{message}\n\nOpen VERA: {app}\nManage or turn off reminders: {manage}"
    return await send_email(to, "A gentle reminder from VERA", html, text=text)


async def deliver(channel: str, reminder: dict, contact: Optional[dict] = None) -> bool:
    """Deliver one reminder over one channel. Returns True on success."""
    contact = contact or {}

    if channel == "in_app":
        # Visibility is handled by the bell/banner; nothing to send.
        return True

    if channel == "email":
        return await _deliver_email(reminder, contact)

    if channel == "sms":
        phone = contact.get("phone_e164")
        if not phone:
            logger.info("SMS channel skipped for reminder %s: no verified phone", reminder.get("id"))
            return False
        return await send_sms(phone, _short_body(reminder))

    if channel == "whatsapp":
        phone = contact.get("phone_e164")
        if not phone:
            logger.info("WhatsApp channel skipped for reminder %s: no verified phone", reminder.get("id"))
            return False
        return await send_whatsapp(phone, _short_body(reminder))

    logger.warning("Unknown channel %r for reminder %s", channel, reminder.get("id"))
    return False
