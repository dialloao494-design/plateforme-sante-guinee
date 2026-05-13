from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
import models
from schemas.notification import NotificationItem
from security import get_current_admin, require_roles
from services.notification_delivery import describe_notification_channels

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def list_notifications(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
):
    """In-app notification history for the authenticated user."""
    rows = (
        db.query(models.NotificationEvent)
        .filter(models.NotificationEvent.user_id == current_user.id)
        .order_by(models.NotificationEvent.created_at.desc())
        .limit(100)
        .all()
    )
    items = [NotificationItem.model_validate(r).model_dump() for r in rows]
    return {"items": items, "message": None if items else "Aucune notification pour le moment."}


@router.get("/channels")
def notification_channels(current_user=Depends(require_roles(["admin", "doctor", "patient"]))):
    """Capability flags for SMS / email / push — driven by environment variables."""
    return describe_notification_channels()


@router.post("/send")
def send_notification(current_user=Depends(get_current_admin)):
    """Admin-only hook for future campaign or test sends."""
    return {"message": "Envoi de masse — non implémenté"}
