"""
Minimal WhatsApp sender via Twilio.

Dev-safe: if Twilio is not configured, it logs the message (number masked). Uses
the Twilio Messages API with `whatsapp:` prefixed numbers. For local testing use
the Twilio WhatsApp sandbox (free). NOTE: in production, sending outside the
24-hour customer-service window requires a pre-approved message template.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)


def _mask(phone: str) -> str:
    return f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else "***"


def _wa(number: str) -> str:
    return number if number.startswith("whatsapp:") else f"whatsapp:{number}"


async def send_whatsapp(to_e164: str, body: str) -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    sender = os.getenv("TWILIO_WHATSAPP_FROM", "").strip()  # e.g. whatsapp:+14155238886

    if not (sid and token and sender):
        logger.info("WHATSAPP (dev, no provider) to=%s\n%s", _mask(to_e164), body)
        return True

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                auth=(sid, token),
                data={"To": _wa(to_e164), "From": _wa(sender), "Body": body},
            )
            resp.raise_for_status()
        return True
    except Exception as exc:  # never raise into the delivery path
        logger.warning("WhatsApp send failed to=%s: %s", _mask(to_e164), type(exc).__name__)
        return False
