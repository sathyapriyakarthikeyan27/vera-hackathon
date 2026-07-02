"""
Minimal transactional email sender.

Dev-safe: if no provider is configured, it logs the message (with the email
address masked) so verification / reset links are visible in local logs without
setting up a provider. In production, set EMAIL_PROVIDER + EMAIL_API_KEY.

This is the shared sender that Phase 0 (verification / reset) and Phase 4 (the
email reminder channel) both use.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)


def _mask(email: str) -> str:
    name, _, domain = email.partition("@")
    head = name[:2] if len(name) > 2 else name[:1]
    return f"{head}***@{domain}" if domain else "***"


async def send_email(to: str, subject: str, html: str, text: str = "") -> bool:
    provider = os.getenv("EMAIL_PROVIDER", "").strip().lower()
    api_key = os.getenv("EMAIL_API_KEY", "").strip()
    sender = os.getenv("EMAIL_FROM", "VERA <no-reply@vera.health>")

    if not provider or not api_key:
        # Dev mode: no provider. Surface the body so links are clickable in logs.
        logger.info(
            "EMAIL (dev, no provider) to=%s subject=%r\n%s",
            _mask(to), subject, text or html,
        )
        return True

    try:
        if provider == "resend":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.resend.com/emails",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={"from": sender, "to": [to], "subject": subject,
                          "html": html, "text": text or None},
                )
                resp.raise_for_status()
            return True

        if provider == "sendgrid":
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={"Authorization": f"Bearer {api_key}"},
                    json={
                        "personalizations": [{"to": [{"email": to}]}],
                        "from": {"email": sender},
                        "subject": subject,
                        "content": [
                            {"type": "text/plain", "value": text or " "},
                            {"type": "text/html", "value": html},
                        ],
                    },
                )
                resp.raise_for_status()
            return True

        logger.warning("Unknown EMAIL_PROVIDER=%r; email not sent to %s", provider, _mask(to))
        return False
    except Exception as exc:  # never raise into the request path
        logger.warning("Email send failed to=%s: %s", _mask(to), type(exc).__name__)
        return False
