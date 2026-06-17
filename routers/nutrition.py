"""Child growth monitoring — nutrition assessments."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from core.clinical_access import resolve_clinic_for_user
from database import get_db
from models.user import User
from schemas.nutrition import NutritionAssessmentCreate, NutritionAssessmentResponse
from security import get_current_user
from services.nutrition_service import NutritionService

router = APIRouter(prefix="/clinical/nutrition", tags=["Nutrition"])

NUTRITION_WRITE_ROLES = ("nutritionist", "midwife", "clinic_admin", "admin")
NUTRITION_READ_ROLES = NUTRITION_WRITE_ROLES + ("doctor", "receptionist", "platform_admin", "platform_owner")


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {list(allowed)}",
        )


@router.get("/patients/{patient_id}/history", response_model=List[NutritionAssessmentResponse])
def nutrition_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NUTRITION_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return NutritionService.list_history(db, clinic_id=clinic.id, patient_id=patient_id)


@router.post("/assessments", response_model=NutritionAssessmentResponse, status_code=status.HTTP_201_CREATED)
def record_assessment(
    body: NutritionAssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NUTRITION_WRITE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return NutritionService.record_assessment(
        db,
        clinic_id=clinic.id,
        patient_id=body.patient_id,
        actor=current_user,
        weight_kg=body.weight_kg,
        height_cm=body.height_cm,
        muac_cm=body.muac_cm,
        age_months=body.age_months,
        consultation_id=body.consultation_id,
        notes=body.notes,
    )
