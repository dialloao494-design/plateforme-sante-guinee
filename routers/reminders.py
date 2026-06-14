"""Appointment reminder and WhatsApp webhook API."""

from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.clinical_access import RECEPTION_ROLES, DOCTOR_ROLES, ADMIN_ROLES, resolve_clinic_for_user
from database import get_db
from models.user import User
from schemas.reminders import ReminderEventResponse, ReminderResponseRequest, StaffNotificationItem
from security import get_current_user
from services.reminder_service import ReminderService
from services.whatsapp_service import WhatsAppService

router = APIRouter(prefix="/clinical/reminders", tags=["Appointment Reminders"])

STAFF_ROLES = RECEPTION_ROLES + DOCTOR_ROLES + ADMIN_ROLES


@router.get("/notifications", response_model=List[StaffNotificationItem])
def staff_notifications(
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff only")
    clinic_id = None
    if current_user.role != "admin":
        clinic = resolve_clinic_for_user(db, current_user)
        clinic_id = clinic.id
    return ReminderService.staff_notifications(db, clinic_id=clinic_id, limit=limit)


@router.post("/appointments/{appointment_id}/respond", response_model=ReminderEventResponse)
def patient_respond(
    appointment_id: int,
    payload: ReminderResponseRequest,
    db: Session = Depends(get_db),
):
    """Patient confirmation/cancellation/reschedule (also via WhatsApp webhook)."""
    try:
        event = ReminderService.handle_patient_response(
            db, appointment_id=appointment_id, action=payload.action, payload=payload.payload
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    rem = event.reminder
    return ReminderEventResponse(
        id=event.id,
        event_type=event.event_type,
        created_at=event.created_at,
        appointment_id=rem.appointment_id if rem else None,
        patient_id=rem.patient_id if rem else None,
    )


@router.get("/whatsapp/webhook")
def whatsapp_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    wa = WhatsAppService()
    if hub_mode == "subscribe" and hub_verify_token == wa.verify_token:
        return int(hub_challenge) if hub_challenge and hub_challenge.isdigit() else hub_challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """WhatsApp Cloud API inbound messages — parse CONFIRMER / ANNULER / REPORTER."""
    body = await request.json()
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return {"status": "ignored"}
        msg = messages[0]
        text = (msg.get("text") or {}).get("body", "").strip().upper()
        # Map phone to appointment via context metadata if available
        context = msg.get("context") or {}
        appointment_id = int(context.get("appointment_id", 0) or os.getenv("WHATSAPP_DEFAULT_APPOINTMENT_ID", "0"))
        if not appointment_id:
            return {"status": "no_appointment_context"}
        action = "confirmed"
        if "ANNUL" in text:
            action = "cancelled"
        elif "REPORT" in text:
            action = "reschedule_requested"
        elif "CONFIR" in text or text in ("OUI", "YES", "OK"):
            action = "confirmed"
        ReminderService.handle_patient_response(db, appointment_id=appointment_id, action=action, payload=text)
        return {"status": "processed", "action": action}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/process-due")
def process_due_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("admin",):
        raise HTTPException(status_code=403, detail="Admin only")
    sent = ReminderService.process_due_reminders(db)
    return {"sent": sent}
