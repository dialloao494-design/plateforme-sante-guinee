from fastapi import APIRouter, HTTPException, Depends
from security import get_current_admin, get_current_doctor, require_roles

router = APIRouter(prefix="/teleconsultation", tags=["Teleconsultation"])


@router.get("/sessions")
def list_sessions(current_user=Depends(require_roles(["admin", "doctor", "patient"]))):
    return {"message": "Teleconsultation session listing TODO"}


@router.post("/sessions")
def create_session(current_user=Depends(get_current_doctor)):
    return {"message": "Teleconsultation session creation TODO"}
