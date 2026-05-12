from fastapi import APIRouter, Depends

from security import get_current_doctor, require_roles

router = APIRouter(prefix="/teleconsultation", tags=["Teleconsultation"])


@router.get("/sessions")
def list_sessions(current_user=Depends(require_roles(["admin", "doctor", "patient"]))):
    """List teleconsultation sessions (placeholder until video provider is integrated)."""
    return {"sessions": [], "message": "No active teleconsultation sessions"}


@router.post("/sessions")
def create_session(current_user=Depends(get_current_doctor)):
    """Create a teleconsultation session (placeholder)."""
    return {"id": None, "message": "Teleconsultation session creation not yet implemented"}
