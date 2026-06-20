"""Nursing care (Soins) REST API."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import models
from core.clinical_access import resolve_clinic_for_user
from database import get_db
from models.user import User
from schemas.nursing_care import (
    NursingDashboardStats,
    NursingMonthlyReport,
    NursingProcedureCreate,
    NursingProcedureResponse,
)
from security import get_current_user
from services.nursing_care_service import NursingCareService

router = APIRouter(prefix="/clinical/nursing-care", tags=["Nursing Care"])

NURSING_WRITE_ROLES = ("nurse", "clinic_admin", "admin", "receptionist")
NURSING_READ_ROLES = NURSING_WRITE_ROLES + (
    "doctor",
    "pev_agent",
    "midwife",
    "platform_admin",
    "platform_owner",
)


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {list(allowed)}",
        )


def _procedure_response(row: models.NursingProcedure) -> NursingProcedureResponse:
    patient_name = None
    if row.patient:
        patient_name = f"{row.patient.first_name} {row.patient.last_name}".strip()
    return NursingProcedureResponse(
        id=row.id,
        clinic_id=row.clinic_id,
        patient_id=row.patient_id,
        procedure_type=row.procedure_type,
        procedure_date=row.procedure_date,
        nurse_user_id=row.nurse_user_id,
        nurse_name=row.nurse_name,
        notes=row.notes,
        procedure_time=row.procedure_time,
        created_at=row.created_at,
        patient_name=patient_name,
    )


@router.get("/dashboard", response_model=NursingDashboardStats)
def nursing_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSING_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return NursingCareService.dashboard_stats(db, clinic_id=clinic.id)


@router.get("/register")
def nursing_register(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSING_READ_ROLES)
    from datetime import date

    today = date.today()
    clinic = resolve_clinic_for_user(db, current_user)
    return NursingCareService.list_register(
        db, clinic_id=clinic.id, year=year or today.year, month=month or today.month
    )


@router.get("/patients/{patient_id}/history", response_model=List[NursingProcedureResponse])
def patient_nursing_history(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSING_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    rows = NursingCareService.list_patient_history(db, clinic_id=clinic.id, patient_id=patient_id)
    return [_procedure_response(r) for r in rows]


@router.get("/reports/monthly", response_model=NursingMonthlyReport)
def nursing_monthly_report(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSING_READ_ROLES)
    from datetime import date

    today = date.today()
    year = year or today.year
    month = month or today.month
    clinic = resolve_clinic_for_user(db, current_user)
    return NursingCareService.monthly_report(db, clinic_id=clinic.id, year=year, month=month)


@router.get("/procedures", response_model=List[NursingProcedureResponse])
def list_procedures(
    procedure_date: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSING_READ_ROLES)
    from datetime import date as date_cls

    clinic = resolve_clinic_for_user(db, current_user)
    parsed = date_cls.fromisoformat(procedure_date) if procedure_date else None
    rows = NursingCareService.list_procedures(db, clinic_id=clinic.id, procedure_date=parsed)
    return [_procedure_response(r) for r in rows]


@router.post("/procedures", response_model=NursingProcedureResponse, status_code=status.HTTP_201_CREATED)
def record_procedure(
    body: NursingProcedureCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSING_WRITE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    row = NursingCareService.record_procedure(
        db,
        clinic_id=clinic.id,
        patient_id=body.patient_id,
        actor=current_user,
        procedure_type=body.procedure_type,
        procedure_date=body.procedure_date,
        procedure_time=body.procedure_time,
        nurse_name=body.nurse_name,
        notes=body.notes,
    )
    db.refresh(row)
    return _procedure_response(row)
