"""Reminders router — in-app notifications for the current user."""

from fastapi import APIRouter, Depends, HTTPException

from routers.auth import get_current_user
from services import reminder_store

router = APIRouter()


@router.get("")
async def list_reminders(user: dict = Depends(get_current_user)):
    return await reminder_store.list_for_user(user["id"])


@router.post("/{reminder_id}/read")
async def read_reminder(reminder_id: str, user: dict = Depends(get_current_user)):
    ok = await reminder_store.mark_read(reminder_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"ok": True}


@router.post("/{reminder_id}/dismiss")
async def dismiss_reminder(reminder_id: str, user: dict = Depends(get_current_user)):
    ok = await reminder_store.dismiss(reminder_id, user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Reminder not found")
    return {"ok": True}
