from fastapi import APIRouter, Depends, HTTPException
import logging
from sqlalchemy.orm import Session

from database import get_db
import models
from security import get_current_admin, require_roles
from services.notification_delivery import describe_notification_channels

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def list_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
):
    """In-app notification history for the authenticated user."""
    try:
        rows = (
            db.query(models.NotificationEvent)
            .filter(models.NotificationEvent.user_id == current_user.id)
            .order_by(models.NotificationEvent.created_at.desc())
            .limit(100)
            .all()
        )
        # Serialize manually so a missing/legacy row never 500s the whole endpoint.
        items = [
            {
                "id": r.id,
                "channel": r.channel,
                "subject": r.subject,
                "body": r.body,
                "meta": r.meta,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
        return {"items": items, "message": None if items else "Aucune notification pour le moment."}
    except Exception:
        logger.exception("list_notifications failed for user_id=%s", getattr(current_user, "id", None))
        raise HTTPException(
            status_code=503,
            detail="Centre de notifications temporairement indisponible",
        )


@router.get("/channels")
def notification_channels(current_user=Depends(require_roles(["admin", "doctor", "patient"]))):
    """Capability flags for SMS / email / push — driven by environment variables."""
    return describe_notification_channels()


@router.post("/send")
def send_notification(current_user=Depends(get_current_admin)):
    """Admin-only hook for future campaign or test sends."""
    return {"message": "Envoi de masse — non implémenté"}
