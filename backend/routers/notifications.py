"""Notification preferences router: channel opt-ins, contact, consent, phone OTP."""

import re
import secrets
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from routers.auth import get_current_user
from services import auth_store, notification_prefs
from services.sms import send_sms

router = APIRouter()

E164 = re.compile(r"^\+[1-9]\d{7,14}$")
VALID_CHANNELS = {"in_app", "email", "sms", "whatsapp"}
OTP_TTL = 600  # 10 minutes


class PrefsBody(BaseModel):
    channel_optin: Optional[dict] = None
    timezone: Optional[str] = Field(default=None, max_length=64)
    quiet_hours_start: Optional[int] = Field(default=None, ge=0, le=23)
    quiet_hours_end: Optional[int] = Field(default=None, ge=0, le=23)
    give_consent: bool = False


class PhoneBody(BaseModel):
    phone: str = Field(..., max_length=20)


class CodeBody(BaseModel):
    code: str = Field(..., min_length=4, max_length=8)


def _response(prefs: dict, user: dict) -> dict:
    return {
        "preferences": prefs,
        "email": user["email"],
        "email_verified": user["email_verified"],
        "consent_version": notification_prefs.CONSENT_VERSION,
    }


@router.get("/preferences")
async def get_preferences(user: dict = Depends(get_current_user)):
    prefs = await notification_prefs.get_or_default(user["id"])
    return _response(prefs, user)


@router.put("/preferences")
async def update_preferences(body: PrefsBody, user: dict = Depends(get_current_user)):
    if body.channel_optin is not None:
        bad = set(body.channel_optin) - VALID_CHANNELS
        if bad:
            raise HTTPException(status_code=422, detail=f"Unknown channels: {', '.join(sorted(bad))}")
        if any(not isinstance(v, bool) for v in body.channel_optin.values()):
            raise HTTPException(status_code=422, detail="Channel opt-ins must be true or false.")

    current = await notification_prefs.get_or_default(user["id"])
    resulting = {**current["channel_optin"], **(body.channel_optin or {})}
    wants_external = any(resulting.get(c) for c in notification_prefs.EXTERNAL_CHANNELS)
    has_consent = bool(current["consent_at"]) or body.give_consent
    if wants_external and not has_consent:
        raise HTTPException(
            status_code=400,
            detail="Please agree to receive reminders before enabling email, SMS, or WhatsApp.",
        )

    prefs = await notification_prefs.upsert(
        user["id"],
        channel_optin=body.channel_optin,
        timezone=body.timezone,
        quiet_hours_start=body.quiet_hours_start,
        quiet_hours_end=body.quiet_hours_end,
        give_consent=body.give_consent,
    )
    return _response(prefs, user)


@router.post("/phone/send-otp")
async def send_phone_otp(body: PhoneBody, user: dict = Depends(get_current_user)):
    if not E164.match(body.phone):
        raise HTTPException(
            status_code=422,
            detail="Enter a valid phone number in international format, for example +14155552671.",
        )
    await notification_prefs.set_phone(user["id"], body.phone)
    code = f"{secrets.randbelow(1_000_000):06d}"
    await auth_store.store_auth_token(user["id"], "otp", code, OTP_TTL)
    await send_sms(body.phone, f"Your VERA verification code is {code}. It expires in 10 minutes.")
    return {"ok": True}


@router.post("/phone/verify")
async def verify_phone_otp(body: CodeBody, user: dict = Depends(get_current_user)):
    ok = await auth_store.consume_user_token(user["id"], "otp", body.code)
    if not ok:
        raise HTTPException(status_code=400, detail="That code is invalid or has expired.")
    await notification_prefs.set_phone_verified(user["id"])
    prefs = await notification_prefs.get_or_default(user["id"])
    return _response(prefs, user)
