"""Phase 2 — unified patient timeline and consolidated Koloma monthly reports."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.clinical_access import resolve_clinic_for_user
from core.tenant import assert_patient_in_clinic
from database import get_db
from models.user import User
from security import get_current_user
from services.hospitalization_service import HospitalizationService
from services.immunization_service import ImmunizationService
from services.lab_clinical_service import LabClinicalService
from services.nursing_care_service import NursingCareService
from services.nutrition_service import NutritionService
from services.patient_timeline_service import PatientTimelineService
from services.pharmacy_clinical_service import PharmacyClinicalService

router = APIRouter(prefix="/clinical", tags=["Clinical Phase 2"])

TIMELINE_ROLES = (
    "receptionist",
    "cashier",
    "doctor",
    "lab_technician",
    "pharmacist",
    "nutritionist",
    "pev_agent",
    "nurse",
    "midwife",
    "clinic_admin",
    "admin",
    "platform_admin",
    "platform_owner",
)


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {list(allowed)}",
        )


@router.get("/patients/{patient_id}/timeline")
def patient_timeline(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, TIMELINE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic.id)
    return PatientTimelineService.build_timeline(db, clinic_id=clinic.id, patient_id=patient_id)


@router.get("/reports/koloma/monthly")
def koloma_monthly_reports(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, TIMELINE_ROLES)
    from datetime import date

    today = date.today()
    year = year or today.year
    month = month or today.month
    clinic = resolve_clinic_for_user(db, current_user)
    cid = clinic.id
    return {
        "year": year,
        "month": month,
        "clinic_id": cid,
        "pev": ImmunizationService.monthly_report(db, clinic_id=cid, year=year, month=month),
        "nursing": NursingCareService.monthly_report(db, clinic_id=cid, year=year, month=month),
        "hospitalization": HospitalizationService.monthly_report(db, clinic_id=cid, year=year, month=month),
        "nutrition": NutritionService.monthly_report(db, clinic_id=cid, year=year, month=month),
        "laboratory": LabClinicalService.monthly_report(db, clinic_id=cid, year=year, month=month),
        "pharmacy": PharmacyClinicalService.monthly_report(db, clinic_id=cid, year=year, month=month),
    }
