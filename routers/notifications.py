from fastapi import APIRouter, Depends
from security import require_roles, get_current_admin

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def list_notifications(current_user=Depends(require_roles(["admin", "doctor", "patient"]))):
    """Reserved for in-app notification center (future)."""
    return {"items": [], "message": "Centre de notifications — à brancher sur la base."}


@router.get("/channels")
def notification_channels(current_user=Depends(require_roles(["admin", "doctor", "patient"]))):
    """
    Capability flags for SMS / email / push reminders.
    Frontend uses this to show "coming soon" UX without failing hard.
    """
    return {
        "enabled": False,
        "channels": [
            {
                "id": "sms",
                "label": "SMS (Orange, MTN)",
                "status": "planned",
                "use_cases": ["rappel_rdv", "teleconsultation", "no_show"],
            },
            {
                "id": "email",
                "label": "Email transactionnel",
                "status": "planned",
                "use_cases": ["confirmation", "recu_paiement"],
            },
            {
                "id": "push",
                "label": "Notifications navigateur",
                "status": "planned",
                "use_cases": ["message_securise"],
            },
        ],
    }


@router.post("/send")
def send_notification(current_user=Depends(get_current_admin)):
    """Admin-only hook for future campaign or test sends."""
    return {"message": "Envoi de masse — non implémenté"}
