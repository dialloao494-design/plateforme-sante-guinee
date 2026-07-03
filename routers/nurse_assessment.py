"""Nurse triage / assessment API — single shared dashboard for all nurses."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

import models
from core.clinical_access import resolve_clinic_for_user
from database import get_db
from models.user import User
from schemas.nurse_assessment import (
    NurseAssessmentCreate,
    NurseAssessmentQueueRow,
    NurseAssessmentResponse,
    NurseDashboardStats,
    NursePatientDetail,
    NursePendingAdmissionRow,
)
from security import get_current_user
from services.nurse_assessment_service import NurseAssessmentService
from services.reception_his_service import ReceptionHisService

router = APIRouter(prefix="/clinical/nurse", tags=["Nurse Assessment"])

NURSE_WRITE_ROLES = ("nurse", "midwife", "clinic_admin", "admin", "receptionist")
NURSE_READ_ROLES = NURSE_WRITE_ROLES + (
    "doctor",
    "lab_technician",
    "pharmacist",
    "platform_admin",
    "platform_owner",
)


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {list(allowed)}",
        )


@router.get("/dashboard", response_model=NurseDashboardStats)
def nurse_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSE_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return NurseAssessmentService.dashboard_stats(db, clinic_id=clinic.id)


@router.get("/patients/{patient_id}/assessment", response_model=Optional[NurseAssessmentResponse])
def get_patient_assessment(
    patient_id: int,
    admission_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSE_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    row = NurseAssessmentService.get_latest(
        db,
        clinic_id=clinic.id,
        patient_id=patient_id,
        admission_id=admission_id,
    )
    if not row:
        return None
    return NurseAssessmentService.serialize(row)


@router.post("/assessments", response_model=NurseAssessmentResponse, status_code=status.HTTP_201_CREATED)
def save_assessment(
    body: NurseAssessmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSE_WRITE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    row = NurseAssessmentService.save_assessment(
        db,
        clinic_id=clinic.id,
        payload=body,
        actor=current_user,
    )
    row = (
        db.query(models.NurseAssessment)
        .options(joinedload(models.NurseAssessment.patient))
        .filter(models.NurseAssessment.id == row.id)
        .first()
    )
    return NurseAssessmentService.serialize(row)


@router.get("/patients/search")
def search_patients(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSE_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    patients = ReceptionHisService.search_patients(db, clinic_id=clinic.id, query=q)
    return patients


@router.get("/patients/{patient_id}", response_model=NursePatientDetail)
def get_nurse_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSE_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    patient = NurseAssessmentService.get_patient_detail(db, clinic_id=clinic.id, patient_id=patient_id)
    return NursePatientDetail.model_validate(patient)


@router.get("/queue/assessments-today", response_model=list[NurseAssessmentQueueRow])
def queue_assessments_today(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSE_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return NurseAssessmentService.list_assessments_today(db, clinic_id=clinic.id)


@router.get("/queue/pending-admissions", response_model=list[NursePendingAdmissionRow])
def queue_pending_admissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, NURSE_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return NurseAssessmentService.list_pending_admissions_today(db, clinic_id=clinic.id)
