"""
Minimal SMS sender.

Dev-safe: if Twilio is not configured, it logs the message (number masked) so
OTP codes are visible in local logs. Real Twilio delivery arrives in Phase 5;
this module is the shared sender used by both phone-OTP verification and the SMS
reminder channel.
"""

import logging
import os

import httpx

logger = logging.getLogger(__name__)


def _mask(phone: str) -> str:
    return f"{phone[:4]}***{phone[-2:]}" if len(phone) > 6 else "***"


async def send_sms(to_e164: str, body: str) -> bool:
    sid = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    token = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    sender = os.getenv("TWILIO_SMS_FROM", "").strip()

    if not (sid and token and sender):
        logger.info("SMS (dev, no provider) to=%s\n%s", _mask(to_e164), body)
        return True

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
                auth=(sid, token),
                data={"To": to_e164, "From": sender, "Body": body},
            )
            resp.raise_for_status()
        return True
    except Exception as exc:  # never raise into the request path
        logger.warning("SMS send failed to=%s: %s", _mask(to_e164), type(exc).__name__)
        return False
