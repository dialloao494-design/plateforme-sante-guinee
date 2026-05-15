"""
Teleconsultation access control — Jitsi / Daily / Twilio-ready room descriptors.
"""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timedelta
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from models.user import User
from services.jitsi_jwt import build_jitsi_jwt, build_jitsi_meeting_url, jitsi_jwt_configured

JOIN_EARLY_MINUTES = int(os.getenv("TELECONSULT_JOIN_EARLY_MINUTES", "15"))
JOIN_LATE_MINUTES = int(os.getenv("TELECONSULT_JOIN_LATE_MINUTES", "30"))
SESSION_GRACE_MINUTES = int(os.getenv("TELECONSULT_SESSION_GRACE_MINUTES", "15"))


def _provider_config() -> dict[str, Any]:
    provider = (os.getenv("TELECONSULT_PROVIDER") or "stub").lower().strip()
    return {
        "provider": provider,
        "jitsi_domain": os.getenv("JITSI_DOMAIN", "meet.jit.si"),
        "jitsi_app_id": os.getenv("JITSI_APP_ID", ""),
        "jitsi_jwt_enabled": jitsi_jwt_configured(),
        "daily_api_key": bool(os.getenv("DAILY_API_KEY")),
        "twilio_configured": bool(os.getenv("TWILIO_API_KEY") and os.getenv("TWILIO_API_SECRET")),
    }


def _room_name(appointment_id: int) -> str:
    salt = os.getenv("SECRET_KEY", "dev")[:16]
    digest = hashlib.sha256(f"{salt}:appt:{appointment_id}".encode()).hexdigest()[:12]
    return f"sante-gn-{appointment_id}-{digest}"


def _user_may_access(appointment: models.RendezVous, user: User, db: Session) -> str:
    if user.role == "admin":
        return "admin"
    if user.role == "doctor":
        doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if doc and doc.id == appointment.doctor_id:
            return "doctor"
    if user.role == "patient":
        pat = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
        if pat and pat.id == appointment.patient_id:
            return "patient"
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not allowed in this consultation")


def _window_bounds(appointment: models.RendezVous) -> tuple[datetime, datetime]:
    start = appointment.date
    if start.tzinfo:
        start = start.replace(tzinfo=None)
    duration = int(appointment.duration_minutes or 30)
    open_at = start - timedelta(minutes=JOIN_EARLY_MINUTES)
    close_at = start + timedelta(minutes=duration + JOIN_LATE_MINUTES + SESSION_GRACE_MINUTES)
    return open_at, close_at


def validate_teleconsult_access(
    appointment_id: int,
    user: User,
    db: Session,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.utcnow()

    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")

    if (appointment.consultation_type or "").lower() != "teleconsultation":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not a teleconsultation appointment")

    status_norm = (appointment.status or "").lower()
    if status_norm in ("cancelled", "expired"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Consultation cancelled or expired")

    role = _user_may_access(appointment, user, db)
    open_at, close_at = _window_bounds(appointment)

    if now < open_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Room opens at {open_at.isoformat(timespec='minutes')} UTC",
        )
    if now > close_at:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Consultation window has ended")

    if status_norm not in ("confirmed", "completed", "checked_in", "active", "paid", "pending"):
        # pending+paid flows still allowed inside window for MVP
        pass

    cfg = _provider_config()
    room = _room_name(appointment.id)
    provider = cfg["provider"]

    display_name = (user.email or f"user-{user.id}").split("@")[0]
    moderator = role in ("doctor", "admin")
    jitsi_token = None
    if provider == "jitsi" and cfg["jitsi_jwt_enabled"]:
        jitsi_token = build_jitsi_jwt(
            room=room,
            display_name=display_name,
            email=user.email,
            moderator=moderator,
        )

    meeting_url = appointment.meeting_link
    if not meeting_url and provider == "jitsi":
        meeting_url = build_jitsi_meeting_url(cfg["jitsi_domain"], room, jitsi_token)
    elif not meeting_url and provider == "stub":
        meeting_url = None

    return {
        "appointment_id": appointment.id,
        "role": role,
        "provider": provider,
        "room_name": room,
        "meeting_url": meeting_url,
        "jitsi_jwt": jitsi_token,
        "jitsi_domain": cfg["jitsi_domain"] if provider == "jitsi" else None,
        "open_at": open_at.isoformat() + "Z",
        "close_at": close_at.isoformat() + "Z",
        "server_time": now.isoformat() + "Z",
        "session_active": open_at <= now <= close_at,
        "can_join": True,
    }


def end_teleconsult_session(appointment_id: int, user: User, db: Session) -> dict[str, Any]:
    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    _user_may_access(appointment, user, db)
    if (appointment.status or "").lower() not in ("cancelled", "completed"):
        appointment.status = "completed"
        db.commit()
    return {"appointment_id": appointment.id, "status": appointment.status, "ended": True}
