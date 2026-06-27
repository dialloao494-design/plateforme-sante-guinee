"""Pharmacy Phase 2 endpoints — dashboard, service requests, patient lookup."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

import models
from core.clinical_access import resolve_clinic_for_user
from core.roles import user_has_any_role
from database import get_db
from models.user import User
from schemas.clinical import DoctorMedicineDeliveryCreate, DoctorMedicineDeliveryResponse
from schemas.pharmacy_his import (
    PharmacyChargePaymentCreate,
    PharmacyPatientOut,
    PharmacyServiceRequestCreate,
    PharmacyServiceRequestResponse,
)
from security import get_current_user
from services.doctor_medicine_delivery_service import DoctorMedicineDeliveryService
from services.pharmacy_clinical_service import PharmacyClinicalService
from services.reception_his_service import ReceptionHisService

router = APIRouter(prefix="/clinical/pharmacy", tags=["Pharmacy Phase 2"])

PHARMACY_READ = ("pharmacist", "doctor", "clinic_admin", "admin", "receptionist", "cashier", "platform_admin", "platform_owner")
PHARMACY_WRITE = ("pharmacist", "clinic_admin", "admin", "doctor")


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    if not user_has_any_role(user.role, allowed):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires one of roles: {list(allowed)}")


def _pharmacy_patient_out(patient: models.Patient) -> PharmacyPatientOut:
    return PharmacyPatientOut(
        id=patient.id,
        patient_number=patient.patient_number,
        qr_token=patient.qr_token,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        age=patient.age or 0,
        gender=patient.gender,
        profession=patient.profession,
        address=patient.address,
        city=patient.city,
        region=patient.region,
        country=patient.country,
        phone=patient.phone,
        quartier=patient.quartier,
    )


@router.get("/patients/search", response_model=List[PharmacyPatientOut])
def search_pharmacy_patients(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    patients = ReceptionHisService.search_patients(db, clinic_id=clinic.id, query=q)
    return [_pharmacy_patient_out(p) for p in patients]


@router.get("/patients/{patient_id}", response_model=PharmacyPatientOut)
def get_pharmacy_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    patient = (
        db.query(models.Patient)
        .filter(
            models.Patient.id == patient_id,
            models.Patient.clinic_id == clinic.id,
            models.Patient.is_archived.is_(False),
        )
        .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    return _pharmacy_patient_out(patient)


@router.post("/service-requests", response_model=PharmacyServiceRequestResponse, status_code=201)
def create_pharmacy_service_request(
    body: PharmacyServiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.create_service_request(
        db, clinic_id=clinic.id, payload=body, actor=current_user
    )


@router.post("/charges/{charge_id}/pay", response_model=PharmacyServiceRequestResponse)
def pay_pharmacy_service_charge(
    charge_id: int,
    body: PharmacyChargePaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.pay_service_charge(
        db,
        clinic_id=clinic.id,
        charge_id=charge_id,
        payload=body,
        actor=current_user,
    )


@router.get("/dashboard")
def pharmacy_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.dashboard_stats(db, clinic_id=clinic.id)


@router.get("/reports/monthly")
def pharmacy_monthly_report(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_READ)
    from datetime import date

    today = date.today()
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.monthly_report(
        db, clinic_id=clinic.id, year=year or today.year, month=month or today.month
    )


@router.get("/doctor-deliveries", response_model=List[DoctorMedicineDeliveryResponse])
def list_doctor_deliveries(
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    rows = DoctorMedicineDeliveryService.list_deliveries(db, clinic_id=clinic.id, limit=limit)
    return rows


@router.post("/doctor-deliveries", response_model=DoctorMedicineDeliveryResponse, status_code=201)
def create_doctor_delivery(
    body: DoctorMedicineDeliveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    return DoctorMedicineDeliveryService.create_delivery(
        db, clinic_id=clinic.id, payload=body, actor=current_user
    )
