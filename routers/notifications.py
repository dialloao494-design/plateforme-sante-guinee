from fastapi import APIRouter, HTTPException, Depends
from security import get_current_admin, require_roles

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("/")
def list_notifications(current_user=Depends(require_roles(["admin", "doctor", "patient"]))):
    return {"message": "Notifications endpoint not implemented yet"}


@router.post("/send")
def send_notification(current_user=Depends(get_current_admin)):
    return {"message": "Notification send endpoint placeholder"}
