from fastapi import APIRouter, Depends
from typing import List
from sqlalchemy.orm import Session
from database import get_db
from security import require_roles
from schemas import rendezvous as rendezvous_schemas
from services.rendezvous_service import RendezVousService

router = APIRouter(prefix="/appointments", tags=["Appointments"])


@router.get("/", response_model=List[rendezvous_schemas.RendezVousWithParticipants])
def list_appointments(
    db: Session = Depends(get_db),
    current_user=Depends(require_roles(["admin", "doctor", "patient"])),
):
    """Return appointments filtered by role.

    - Patients: only their own appointments
    - Doctors: only their own appointments
    - Admins: all appointments
    """
    return RendezVousService.list_appointments_for_user(current_user, db)
