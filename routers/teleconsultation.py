from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models.user import User
from security import require_roles
from services.teleconsultation_access import (
    end_teleconsult_session,
    evaluate_teleconsult_room,
    validate_teleconsult_access,
)

router = APIRouter(prefix="/teleconsultation", tags=["Teleconsultation"])


@router.get("/appointments/{appointment_id}/room-status")
def get_consultation_room_status(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "doctor", "patient"])),
):
    """
    Eligibility probe for the consultation UI (does not expose JWT / meeting secrets).
    Always returns 200 with can_join + French message for patient/doctor dashboards.
    """
    return evaluate_teleconsult_room(appointment_id, current_user, db)


@router.get("/appointments/{appointment_id}/access")
def get_consultation_access(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "doctor", "patient"])),
):
    """
    Secure room descriptor for an appointment (time-boxed).
    Frontend uses this before opening Jitsi/Daily/Twilio or in-app stub room.
    """
    return validate_teleconsult_access(appointment_id, current_user, db)


@router.post("/appointments/{appointment_id}/end")
def end_consultation(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "doctor", "patient"])),
):
    """Mark consultation completed and invalidate further joins after grace period."""
    return end_teleconsult_session(appointment_id, current_user, db)


@router.get("/config")
def teleconsult_config(current_user=Depends(require_roles(["admin", "doctor", "patient"]))):
    """Non-secret provider hints for UI."""
    import os

    from services.jitsi_jwt import jitsi_jwt_configured

    from services.teleconsult_room import effective_jitsi_embed_domain, embed_block_reason, jitsi_embed_mode

    provider = (os.getenv("TELECONSULT_PROVIDER") or "jitsi").lower()
    if provider == "stub":
        provider = "jitsi"
    return {
        "provider": provider,
        "jitsi_domain": effective_jitsi_embed_domain(),
        "jitsi_embed_mode": jitsi_embed_mode(),
        "embed_ready": embed_block_reason() is None,
        "embed_block_reason": embed_block_reason(),
        "jitsi_jwt_enabled": jitsi_jwt_configured(),
        "features": {
            "access_validation": True,
            "auto_end_on_leave": True,
            "websocket_live": True,
        },
    }
