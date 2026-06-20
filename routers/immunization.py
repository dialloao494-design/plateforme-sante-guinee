"""PEV immunization — schedule, history, due and missed vaccines."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.clinical_access import resolve_clinic_for_user
from database import get_db
from models.user import User
from schemas.immunization import (
    ImmunizationDashboardStats,
    ImmunizationMonthlyReport,
    ImmunizationRecordCreate,
    ImmunizationRecordResponse,
    ImmunizationStatusResponse,
    VaccineDueItem,
    VaccineScheduleItemResponse,
)
from security import get_current_user
from services.immunization_service import ImmunizationService

router = APIRouter(prefix="/clinical/immunization", tags=["Immunization"])

IMMUNIZATION_WRITE_ROLES = ("pev_agent", "midwife", "clinic_admin", "admin", "receptionist")
IMMUNIZATION_READ_ROLES = IMMUNIZATION_WRITE_ROLES + (
    "doctor",
    "nutritionist",
    "nurse",
    "platform_admin",
    "platform_owner",
)


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {list(allowed)}",
        )


@router.get("/dashboard", response_model=ImmunizationDashboardStats)
def immunization_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, IMMUNIZATION_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return ImmunizationService.dashboard_stats(db, clinic_id=clinic.id)


@router.get("/reports/monthly", response_model=ImmunizationMonthlyReport)
def immunization_monthly_report(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, IMMUNIZATION_READ_ROLES)
    from datetime import date

    today = date.today()
    year = year or today.year
    month = month or today.month
    clinic = resolve_clinic_for_user(db, current_user)
    data = ImmunizationService.monthly_report(db, clinic_id=clinic.id, year=year, month=month)
    return ImmunizationMonthlyReport(
        year=data["year"],
        month=data["month"],
        total_vaccinations=data["total_vaccinations"],
        by_vaccine_type=data["by_vaccine_type"],
        by_age_group=data["by_age_group"],
        records=[ImmunizationRecordResponse.model_validate(r) for r in data["records"]],
    )


@router.get("/schedule", response_model=List[VaccineScheduleItemResponse])
def vaccination_schedule(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, IMMUNIZATION_READ_ROLES)
    return ImmunizationService.list_schedule(db)


@router.get("/patients/{patient_id}/history", response_model=List[ImmunizationRecordResponse])
def vaccination_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, IMMUNIZATION_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return ImmunizationService.list_history(db, clinic_id=clinic.id, patient_id=patient_id)


@router.get("/patients/{patient_id}/status", response_model=ImmunizationStatusResponse)
def vaccination_status(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, IMMUNIZATION_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    data = ImmunizationService.compute_due_and_missed(db, clinic_id=clinic.id, patient_id=patient_id)
    return ImmunizationStatusResponse(
        due=[VaccineDueItem(**x) for x in data["due"]],
        missed=[VaccineDueItem(**x) for x in data["missed"]],
        upcoming=[VaccineDueItem(**x) for x in data["upcoming"]],
    )


@router.post("/records", response_model=ImmunizationRecordResponse, status_code=status.HTTP_201_CREATED)
def record_vaccination(
    body: ImmunizationRecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, IMMUNIZATION_WRITE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return ImmunizationService.record_vaccination(
        db,
        clinic_id=clinic.id,
        patient_id=body.patient_id,
        actor=current_user,
        vaccine_code=body.vaccine_code,
        vaccine_name=body.vaccine_name,
        administered_at=body.administered_at,
        dose_label=body.dose_label,
        dose_number=body.dose_number,
        batch_number=body.batch_number,
        next_appointment_date=body.next_appointment_date,
        vaccinator_name=body.vaccinator_name,
        notes=body.notes,
    )
