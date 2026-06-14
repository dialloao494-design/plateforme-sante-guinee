"""Medical history and follow-up API."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

import schemas.medical_history as mh_schemas
import models
from core.http_utils import client_ip
from database import get_db
from models.user import User
from security import get_current_user, require_roles
from services.medical_history_service import MedicalHistoryService
from services.patient_record_access import PatientRecordAccessPolicy

router = APIRouter(prefix="/patients", tags=["Medical History"])

READ_ROLES = ["admin", "doctor", "patient", "receptionist", "lab_technician", "pharmacist"]
WRITE_ROLES = ["admin", "doctor", "receptionist"]


@router.get("/me/medical-history", response_model=mh_schemas.PatientMedicalHistoryResponse)
def my_medical_history(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["patient"])),
):
    patient = db.query(models.Patient).filter(models.Patient.user_id == current_user.id).first()
    if not patient:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Patient profile not found")
    return MedicalHistoryService.get_full_history(
        db, patient.id, current_user, client_ip=client_ip(request)
    )


@router.get("/{patient_id}/medical-history", response_model=mh_schemas.PatientMedicalHistoryResponse)
def patient_medical_history(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(READ_ROLES)),
):
    return MedicalHistoryService.get_full_history(
        db, patient_id, current_user, client_ip=client_ip(request)
    )


@router.get("/{patient_id}/timeline-grouped", response_model=List[mh_schemas.TimelineDayGroup])
def patient_timeline_grouped(
    patient_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(READ_ROLES)),
):
    PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)
    return MedicalHistoryService.build_grouped_timeline(db, patient_id)


@router.patch("/{patient_id}/medical-record", response_model=mh_schemas.PatientMedicalRecordResponse)
def update_medical_record(
    patient_id: int,
    payload: mh_schemas.PatientMedicalRecordUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(WRITE_ROLES)),
):
    return MedicalHistoryService.update_record(
        db, patient_id, payload, current_user, client_ip=client_ip(request)
    )


@router.post("/{patient_id}/allergies", response_model=mh_schemas.PatientAllergyResponse, status_code=201)
def add_allergy(
    patient_id: int,
    payload: mh_schemas.PatientAllergyCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(WRITE_ROLES)),
):
    return MedicalHistoryService.add_allergy(
        db, patient_id, payload, current_user, client_ip=client_ip(request)
    )


@router.delete("/{patient_id}/allergies/{allergy_id}", status_code=204)
def remove_allergy(
    patient_id: int,
    allergy_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(WRITE_ROLES)),
):
    MedicalHistoryService.soft_delete_allergy(
        db, patient_id, allergy_id, current_user, client_ip=client_ip(request)
    )


@router.post(
    "/{patient_id}/chronic-conditions",
    response_model=mh_schemas.PatientChronicConditionResponse,
    status_code=201,
)
def add_chronic_condition(
    patient_id: int,
    payload: mh_schemas.PatientChronicConditionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(WRITE_ROLES)),
):
    return MedicalHistoryService.add_chronic_condition(
        db, patient_id, payload, current_user, client_ip=client_ip(request)
    )


@router.post("/{patient_id}/vitals", response_model=mh_schemas.PatientVitalSignsResponse, status_code=201)
def record_vitals(
    patient_id: int,
    payload: mh_schemas.PatientVitalSignsCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(WRITE_ROLES)),
):
    return MedicalHistoryService.record_vitals(
        db, patient_id, payload, current_user, client_ip=client_ip(request)
    )
