"""Appointment reminder and WhatsApp webhook API."""

from __future__ import annotations

import os
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from core.clinical_access import RECEPTION_ROLES, DOCTOR_ROLES, ADMIN_ROLES, resolve_clinic_for_user
from core.reminder_security import verify_reminder_respond_token
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
    from core.roles import PLATFORM_SCOPE_ROLES, user_has_any_role

    clinic_id = None
    if user_has_any_role(current_user.role, PLATFORM_SCOPE_ROLES):
        clinic_id = None  # platform may see all
    else:
        clinic = resolve_clinic_for_user(db, current_user)
        if clinic is None or clinic.id is None:
            raise HTTPException(status_code=403, detail="Clinic scope required")
        clinic_id = clinic.id
    return ReminderService.staff_notifications(db, clinic_id=clinic_id, limit=limit)


@router.post("/appointments/{appointment_id}/respond", response_model=ReminderEventResponse)
def patient_respond(
    request: Request,
    appointment_id: int,
    submission: ReminderResponseRequest,
    db: Session = Depends(get_db),
):
    """Patient confirmation/cancellation/reschedule (also via WhatsApp webhook)."""
    if not verify_reminder_respond_token(appointment_id, submission.token):
        raise HTTPException(status_code=403, detail="Invalid reminder response token")
    try:
        event = ReminderService.handle_patient_response(
            db,
            appointment_id=appointment_id,
            action=submission.action,
            payload=submission.payload,
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
    if not wa.verify_token:
        raise HTTPException(status_code=403, detail="WhatsApp verify token not configured")
    if hub_mode == "subscribe" and hub_verify_token == wa.verify_token:
        return int(hub_challenge) if hub_challenge and hub_challenge.isdigit() else hub_challenge
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    """WhatsApp Cloud API inbound messages — parse CONFIRMER / ANNULER / REPORTER.

    Authenticity is enforced via Meta X-Hub-Signature-256 (WHATSAPP_APP_SECRET).
    """
    from core.whatsapp_webhook_security import (
        WhatsAppWebhookAuthError,
        verify_whatsapp_signature,
    )

    raw_body = await request.body()
    try:
        verify_whatsapp_signature(
            raw_body=raw_body,
            signature_header=request.headers.get("X-Hub-Signature-256")
            or request.headers.get("x-hub-signature-256"),
        )
    except WhatsAppWebhookAuthError as exc:
        raise HTTPException(status_code=403, detail="Webhook authentication failed") from exc

    import json as _json

    try:
        body = _json.loads(raw_body.decode("utf-8") or "{}")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")
    try:
        entry = body.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return {"status": "ignored"}
        msg = messages[0]
        text = (msg.get("text") or {}).get("body", "").strip().upper()
        from_phone = msg.get("from", "")
        context = msg.get("context") or {}
        appointment_id = int(context.get("appointment_id", 0) or 0)
        if not appointment_id and from_phone:
            appointment_id = ReminderService.resolve_appointment_id_by_phone(db, from_phone) or 0
        # Never fall back to a default appointment id — that enables cross-patient mutation.
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
    except HTTPException:
        raise
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}


@router.post("/process-due")
def process_due_reminders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from core.roles import PLATFORM_SCOPE_ROLES, user_has_any_role

    if not user_has_any_role(current_user.role, PLATFORM_SCOPE_ROLES):
        raise HTTPException(status_code=403, detail="Platform admin only")
    sent = ReminderService.process_due_reminders(db)
    return {"sent": sent}
