"""

Teleconsultation access control — Jitsi embedded room descriptors.



Appointment dates are stored as naive local datetimes (HTML datetime-local / rendezvous

validation uses datetime.now()). All window checks MUST use datetime.now(), not utcnow().

"""



from __future__ import annotations



import os

from datetime import datetime, timedelta

from typing import Any



from fastapi import HTTPException, status

from sqlalchemy.orm import Session



import models

from core.payment_access_policy import (
    BUSINESS_ACTIVE_APPOINTMENT_STATUSES,
    PaymentAccessPolicy,
)
from core.teleconsult_exposure_policy import TeleconsultExposurePolicy
from models.user import User

from services.jitsi_jwt import build_jitsi_jwt, jitsi_jwt_configured

from services.teleconsult_room import (
    effective_jitsi_embed_domain,
    embed_block_reason,
    jitsi_app_id,
    jitsi_embed_mode,
    meeting_link_for_appointment,
    room_name,
)



JOIN_EARLY_MINUTES = int(os.getenv("TELECONSULT_JOIN_EARLY_MINUTES", "15"))

JOIN_LATE_MINUTES = int(os.getenv("TELECONSULT_JOIN_LATE_MINUTES", "30"))

SESSION_GRACE_MINUTES = int(os.getenv("TELECONSULT_SESSION_GRACE_MINUTES", "15"))

# Re-export for backward compatibility — canonical list lives in PaymentAccessPolicy.
JOINABLE_STATUSES = BUSINESS_ACTIVE_APPOINTMENT_STATUSES





def _now_local() -> datetime:

    """Wall-clock now — matches naive appointment.date from datetime-local inputs."""

    return datetime.now()





def _normalize_naive_dt(value: datetime) -> datetime:

    if value.tzinfo is not None:

        return value.replace(tzinfo=None)

    return value





def _provider_config() -> dict[str, Any]:

    provider = (os.getenv("TELECONSULT_PROVIDER") or "jitsi").lower().strip()

    if provider == "stub":

        provider = "jitsi"

    mode = jitsi_embed_mode()

    return {

        "provider": provider,

        "jitsi_domain": effective_jitsi_embed_domain(),

        "jitsi_app_id": jitsi_app_id(),

        "jitsi_embed_mode": mode,

        "jitsi_jwt_enabled": jitsi_jwt_configured(),

        "embed_ready": mode != "blocked" and (mode != "jaas" or jitsi_jwt_configured()),

        "embed_block_reason": embed_block_reason(),

        "daily_api_key": bool(os.getenv("DAILY_API_KEY")),

        "twilio_configured": bool(os.getenv("TWILIO_API_KEY") and os.getenv("TWILIO_API_SECRET")),

    }





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

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Accès refusé à cette téléconsultation.")





def _window_bounds(appointment: models.RendezVous) -> tuple[datetime, datetime]:

    start = _normalize_naive_dt(appointment.date)

    duration = int(appointment.duration_minutes or 30)

    open_at = start - timedelta(minutes=JOIN_EARLY_MINUTES)

    close_at = start + timedelta(minutes=duration + JOIN_LATE_MINUTES + SESSION_GRACE_MINUTES)

    return open_at, close_at





def _format_local_dt(dt: datetime) -> str:

    return _normalize_naive_dt(dt).strftime("%d/%m/%Y %H:%M")





def _build_access_payload(

    appointment: models.RendezVous,

    user: User,

    role: str,

    *,

    now: datetime,

    open_at: datetime,

    close_at: datetime,

    include_credentials: bool = True,

) -> dict[str, Any]:

    cfg = _provider_config()

    room = room_name(appointment.id)

    domain = cfg["jitsi_domain"]

    provider = cfg["provider"]



    display_name = (user.email or f"user-{user.id}").split("@")[0]

    moderator = role in ("doctor", "admin")



    jitsi_token = None

    if provider == "jitsi" and cfg["jitsi_embed_mode"] in ("jaas", "self_hosted_jwt") and cfg["jitsi_jwt_enabled"]:

        jitsi_token = build_jitsi_jwt(

            room=room,

            display_name=display_name,

            email=user.email,

            moderator=moderator,

        )



    meeting_url = meeting_link_for_appointment(appointment.id, domain=domain, jwt_token=jitsi_token)



    payload: dict[str, Any] = {

        "appointment_id": appointment.id,

        "role": role,

        "provider": provider,

        "embed_mode": "jitsi_iframe",

        "room_name": room,

        "jitsi_domain": domain,

        "open_at": open_at.isoformat(),

        "close_at": close_at.isoformat(),

        "server_time": now.isoformat(),

        "session_active": open_at <= now <= close_at,

        "can_join": True,

        "display_name": display_name,

        "email": user.email,

        "is_moderator": moderator,

        "jitsi_app_id": cfg["jitsi_app_id"] or None,

        "jitsi_embed_mode": cfg["jitsi_embed_mode"],

        "embed_ready": cfg["embed_ready"],

        "embed_block_reason": cfg["embed_block_reason"],

    }



    if include_credentials:
        if TeleconsultExposurePolicy.may_issue_join_credentials(appointment):
            payload["meeting_url"] = meeting_url
            payload["jitsi_jwt"] = jitsi_token
        else:
            payload["meeting_url"] = None
            payload["jitsi_jwt"] = None
    else:
        payload["meeting_url"] = None
        payload["jitsi_jwt"] = None



    return payload





def evaluate_teleconsult_room(

    appointment_id: int,

    user: User,

    db: Session,

    *,

    now: datetime | None = None,

) -> dict[str, Any]:

    """

    Non-throwing eligibility check for UI (room-status endpoint).

    Returns can_join + reason + French message.

    """

    now = _normalize_naive_dt(now or _now_local())



    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()

    if not appointment:

        return {

            "appointment_id": appointment_id,

            "can_join": False,

            "reason": "not_found",

            "message": "Rendez-vous introuvable.",

        }



    if (appointment.consultation_type or "").lower() != "teleconsultation":

        return {

            "appointment_id": appointment.id,

            "can_join": False,

            "reason": "not_teleconsultation",

            "message": "Ce rendez-vous n'est pas une téléconsultation.",

        }



    status_norm = (appointment.status or "").lower()

    if status_norm in ("cancelled", "expired"):

        return {

            "appointment_id": appointment.id,

            "can_join": False,

            "reason": "cancelled",

            "message": "Cette téléconsultation est annulée ou expirée.",

            "status": appointment.status,

        }



    try:

        role = _user_may_access(appointment, user, db)

    except HTTPException:

        return {

            "appointment_id": appointment.id,

            "can_join": False,

            "reason": "forbidden",

            "message": "Vous n'êtes pas autorisé à accéder à cette téléconsultation.",

        }



    payment_block = PaymentAccessPolicy.evaluate_teleconsult_gate(appointment)

    if payment_block:

        return {

            "appointment_id": appointment.id,

            **payment_block,

        }



    open_at, close_at = _window_bounds(appointment)



    if now < open_at:

        minutes = max(1, int((open_at - now).total_seconds() // 60) + 1)

        return {

            "appointment_id": appointment.id,

            "can_join": False,

            "reason": "too_early",

            "message": f"La salle ouvre à {_format_local_dt(open_at)} (dans environ {minutes} min).",

            "open_at": open_at.isoformat(),

            "close_at": close_at.isoformat(),

            "server_time": now.isoformat(),

            "minutes_until_open": minutes,

            "role": role,

        }



    if now > close_at:

        return {

            "appointment_id": appointment.id,

            "can_join": False,

            "reason": "too_late",

            "message": "La fenêtre de téléconsultation est terminée.",

            "open_at": open_at.isoformat(),

            "close_at": close_at.isoformat(),

            "server_time": now.isoformat(),

            "role": role,

        }



    payload = _build_access_payload(

        appointment, user, role, now=now, open_at=open_at, close_at=close_at, include_credentials=False

    )

    payload["can_join"] = True

    payload["reason"] = "ok"

    payload["message"] = "Vous pouvez rejoindre la salle."

    return payload





def validate_teleconsult_access(

    appointment_id: int,

    user: User,

    db: Session,

    *,

    now: datetime | None = None,

) -> dict[str, Any]:

    now = _normalize_naive_dt(now or _now_local())



    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()

    if not appointment:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendez-vous introuvable.")



    if (appointment.consultation_type or "").lower() != "teleconsultation":

        raise HTTPException(

            status_code=status.HTTP_400_BAD_REQUEST,

            detail="Ce rendez-vous n'est pas une téléconsultation.",

        )



    status_norm = (appointment.status or "").lower()

    if status_norm in ("cancelled", "expired"):

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail="Cette téléconsultation est annulée ou expirée.",

        )



    role = _user_may_access(appointment, user, db)

    PaymentAccessPolicy.assert_teleconsult_access(appointment)

    open_at, close_at = _window_bounds(appointment)



    if now < open_at:

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail=f"La salle ouvre à {_format_local_dt(open_at)}.",

        )

    if now > close_at:

        raise HTTPException(

            status_code=status.HTTP_403_FORBIDDEN,

            detail="La fenêtre de téléconsultation est terminée.",

        )



    return _build_access_payload(appointment, user, role, now=now, open_at=open_at, close_at=close_at)





def end_teleconsult_session(appointment_id: int, user: User, db: Session) -> dict[str, Any]:

    appointment = db.query(models.RendezVous).filter(models.RendezVous.id == appointment_id).first()

    if not appointment:

        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rendez-vous introuvable.")

    _user_may_access(appointment, user, db)

    if (appointment.status or "").lower() not in ("cancelled", "completed"):

        appointment.status = "completed"

        db.commit()

    return {"appointment_id": appointment.id, "status": appointment.status, "ended": True}


