"""
Authentication router: email + password and Google OAuth.

- Access token: stateless JWT in an httpOnly cookie (short-lived).
- Refresh token: opaque, DB-backed, rotated on use, in an httpOnly cookie.
- Email verification + password reset via single-use emailed tokens.
"""

import logging
import os
from typing import Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field

from services import auth_store, security
from services.email import send_email

logger = logging.getLogger(__name__)
router = APIRouter()

COOKIE_ACCESS = "vera_access"
COOKIE_REFRESH = "vera_refresh"

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"


# ── Cookie helpers ───────────────────────────────────────────────────────────

def _cookie_kwargs() -> dict:
    # COOKIE_SECURE=true in production (HTTPS). Lax lets the OAuth redirect carry cookies.
    secure = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    return {"httponly": True, "secure": secure, "samesite": "lax", "path": "/"}


def _app_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost").rstrip("/")


async def _issue_session(response: Response, user_id: str) -> None:
    """Mint a fresh access + refresh pair and set them as cookies."""
    access = security.create_access_token(user_id)
    refresh = security.new_token()
    await auth_store.store_auth_token(user_id, "refresh", refresh, security.REFRESH_TTL)
    kw = _cookie_kwargs()
    response.set_cookie(COOKIE_ACCESS, access, max_age=security.ACCESS_TTL, **kw)
    response.set_cookie(COOKIE_REFRESH, refresh, max_age=security.REFRESH_TTL, **kw)


def _clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_ACCESS, path="/")
    response.delete_cookie(COOKIE_REFRESH, path="/")


# ── Dependencies ─────────────────────────────────────────────────────────────

async def get_current_user(request: Request) -> dict:
    token = request.cookies.get(COOKIE_ACCESS)
    payload = security.decode_token(token, "access") if token else None
    if not payload:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await auth_store.get_user_by_id(payload.get("sub", ""))
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


async def get_optional_user(request: Request) -> Optional[dict]:
    try:
        return await get_current_user(request)
    except HTTPException:
        return None


# ── Schemas ──────────────────────────────────────────────────────────────────

class SignupBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    name: Optional[str] = Field(default=None, max_length=100)
    session_id: Optional[str] = None


class LoginBody(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    session_id: Optional[str] = None


class EmailBody(BaseModel):
    email: EmailStr


class TokenBody(BaseModel):
    token: str


class ResetBody(BaseModel):
    token: str
    password: str = Field(..., min_length=8, max_length=128)


# ── Email + password ─────────────────────────────────────────────────────────

@router.post("/signup", status_code=201)
async def signup(body: SignupBody, response: Response):
    existing = await auth_store.get_user_by_email(body.email)
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    user = await auth_store.create_user(
        email=body.email,
        password_hash=security.hash_password(body.password),
        name=body.name,
        email_verified=False,
    )
    if body.session_id:
        await auth_store.attach_session_to_user(body.session_id, user["id"])

    await _send_verification_email(user["id"], user["email"])
    await _issue_session(response, user["id"])
    return {"user": user}


@router.post("/login")
async def login(body: LoginBody, response: Response):
    row = await auth_store.get_user_by_email(body.email)
    if not row or not security.verify_password(body.password, row.get("password_hash") or ""):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    user_id = str(row["id"])
    # Opportunistic rehash if Argon2 parameters have since been strengthened.
    if security.needs_rehash(row["password_hash"]):
        await auth_store.set_password(user_id, security.hash_password(body.password))
    if body.session_id:
        await auth_store.attach_session_to_user(body.session_id, user_id)

    await _issue_session(response, user_id)
    return {"user": auth_store._public_user(row)}


@router.post("/logout")
async def logout(request: Request, response: Response):
    refresh = request.cookies.get(COOKIE_REFRESH)
    if refresh:
        user_id = await auth_store.consume_auth_token("refresh", refresh)
        if user_id:
            await auth_store.revoke_refresh_tokens(user_id)
    _clear_session(response)
    return {"ok": True}


@router.post("/refresh")
async def refresh(request: Request, response: Response):
    token = request.cookies.get(COOKIE_REFRESH)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user_id = await auth_store.consume_auth_token("refresh", token)
    if not user_id:
        _clear_session(response)
        raise HTTPException(status_code=401, detail="Session expired")
    await _issue_session(response, user_id)  # rotation: old token already marked used
    user = await auth_store.get_user_by_id(user_id)
    return {"user": user}


@router.get("/me")
async def me(user: dict = Depends(get_current_user)):
    return {"user": user}


class LinkSessionBody(BaseModel):
    session_id: str


@router.post("/link-session")
async def link_session(body: LinkSessionBody, user: dict = Depends(get_current_user)):
    ok = await auth_store.attach_session_to_user(body.session_id, user["id"])
    return {"ok": ok}


@router.post("/verify-email")
async def verify_email(body: TokenBody):
    user_id = await auth_store.consume_auth_token("email_verify", body.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="This verification link is invalid or has expired.")
    await auth_store.set_email_verified(user_id)
    return {"ok": True}


@router.post("/request-reset")
async def request_reset(body: EmailBody):
    # Always 200 — never reveal whether an account exists.
    row = await auth_store.get_user_by_email(body.email)
    if row:
        token = security.new_token()
        await auth_store.store_auth_token(str(row["id"]), "password_reset", token, security.RESET_TTL)
        link = f"{_app_base_url()}/reset-password?token={token}"
        await send_email(
            row["email"],
            "Reset your VERA password",
            f'<p>You asked to reset your password. <a href="{link}">Choose a new password</a>. '
            f"This link expires in 1 hour. If you did not ask for this, you can ignore this email.</p>",
            text=f"Reset your VERA password: {link} (expires in 1 hour).",
        )
    return {"ok": True}


@router.post("/reset")
async def reset(body: ResetBody):
    user_id = await auth_store.consume_auth_token("password_reset", body.token)
    if not user_id:
        raise HTTPException(status_code=400, detail="This reset link is invalid or has expired.")
    await auth_store.set_password(user_id, security.hash_password(body.password))
    await auth_store.revoke_refresh_tokens(user_id)  # force re-login everywhere
    return {"ok": True}


async def _send_verification_email(user_id: str, email: str) -> None:
    token = security.new_token()
    await auth_store.store_auth_token(user_id, "email_verify", token, security.EMAIL_VERIFY_TTL)
    link = f"{_app_base_url()}/verify-email?token={token}"
    await send_email(
        email,
        "Confirm your VERA email",
        f'<p>Welcome to VERA. Please <a href="{link}">confirm your email</a> to secure your account. '
        f"This link expires in 24 hours.</p>",
        text=f"Confirm your VERA email: {link} (expires in 24 hours).",
    )


# ── Google OAuth ─────────────────────────────────────────────────────────────

def _google_config() -> Optional[dict]:
    cid = os.getenv("GOOGLE_CLIENT_ID")
    secret = os.getenv("GOOGLE_CLIENT_SECRET")
    if not cid or not secret:
        return None
    redirect = os.getenv("GOOGLE_REDIRECT_URI", f"{_app_base_url()}/api/auth/google/callback")
    return {"client_id": cid, "client_secret": secret, "redirect_uri": redirect}


@router.get("/google/login")
async def google_login(session_id: Optional[str] = None):
    cfg = _google_config()
    if not cfg:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")
    state = security.create_state_token({"session_id": session_id})
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(code: Optional[str] = None, state: Optional[str] = None):
    cfg = _google_config()
    if not cfg:
        raise HTTPException(status_code=503, detail="Google sign-in is not configured.")

    state_payload = security.decode_token(state or "", "oauth_state")
    if not code or not state_payload:
        return RedirectResponse(f"{_app_base_url()}/login?error=oauth")

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.post(GOOGLE_TOKEN_URL, data={
                "code": code,
                "client_id": cfg["client_id"],
                "client_secret": cfg["client_secret"],
                "redirect_uri": cfg["redirect_uri"],
                "grant_type": "authorization_code",
            })
            token_resp.raise_for_status()
            access_token = token_resp.json().get("access_token")

            info_resp = await client.get(
                GOOGLE_USERINFO_URL,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            info_resp.raise_for_status()
            info = info_resp.json()
    except Exception as exc:
        logger.warning("Google OAuth exchange failed: %s", type(exc).__name__)
        return RedirectResponse(f"{_app_base_url()}/login?error=oauth")

    provider_account_id = info.get("sub")
    email = (info.get("email") or "").lower()
    if not provider_account_id or not email:
        return RedirectResponse(f"{_app_base_url()}/login?error=oauth")

    user = await auth_store.get_user_by_oauth("google", provider_account_id)
    if not user:
        existing = await auth_store.get_user_by_email(email)
        if existing:
            user = auth_store._public_user(existing)
        else:
            user = await auth_store.create_user(
                email=email, password_hash=None, name=info.get("name"),
                email_verified=bool(info.get("email_verified", True)),
            )
        await auth_store.link_oauth_account(user["id"], "google", provider_account_id)

    session_id = state_payload.get("session_id")
    if session_id:
        await auth_store.attach_session_to_user(session_id, user["id"])

    redirect = RedirectResponse(f"{_app_base_url()}/assessment")
    await _issue_session(redirect, user["id"])
    return redirect
