"""Admission and hospitalization REST API."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

import models
from core.clinical_access import resolve_clinic_for_user, user_clinic_id
from core.http_utils import client_ip
from database import get_db
from models.user import User
from schemas.hospitalization import (
    AdmissionCreate,
    AdmissionResponse,
    AdmissionStatusUpdate,
    BedAssignmentRequest,
    HospitalBedCreate,
    HospitalBedResponse,
    HospitalBedUpdate,
    HospitalizationDashboardStats,
    HospitalRoomCreate,
    HospitalRoomResponse,
    HospitalRoomUpdate,
    OccupancySummary,
    PatientStayResponse,
)
from security import get_current_user
from services.hospitalization_service import HospitalizationService

router = APIRouter(prefix="/clinical/hospitalization", tags=["Hospitalization"])

ADMISSION_ROLES = ("platform_owner", "platform_admin", "clinic_admin", "admin", "doctor", "receptionist", "nurse")
BED_ADMIN_ROLES = ("platform_owner", "platform_admin", "clinic_admin", "admin", "receptionist")


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    from fastapi import HTTPException, status

    if user.role not in allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires one of roles: {list(allowed)}",
        )


def _bed_response(bed: models.HospitalBed) -> HospitalBedResponse:
    room = bed.room
    return HospitalBedResponse(
        id=bed.id,
        room_id=bed.room_id,
        bed_number=bed.bed_number,
        status=bed.status,
        ward_name=room.ward_name if room else None,
        room_number=room.room_number if room else None,
    )


def _admission_response(admission: models.Admission) -> AdmissionResponse:
    patient_name = None
    if admission.patient:
        patient_name = f"{admission.patient.first_name} {admission.patient.last_name}".strip()
    attending_name = None
    current_bed = None
    stays_out: list[PatientStayResponse] = []
    for stay in admission.stays or []:
        bed = stay.bed
        room = bed.room if bed else None
        sr = PatientStayResponse(
            id=stay.id,
            admission_id=stay.admission_id,
            bed_id=stay.bed_id,
            assigned_at=stay.assigned_at,
            released_at=stay.released_at,
            is_current=stay.is_current,
            transfer_reason=stay.transfer_reason,
            bed_number=bed.bed_number if bed else None,
            room_number=room.room_number if room else None,
            ward_name=room.ward_name if room else None,
        )
        stays_out.append(sr)
        if stay.is_current and bed:
            current_bed = _bed_response(bed)
    length_of_stay = None
    if admission.admitted_at and admission.discharged_at:
        length_of_stay = round((admission.discharged_at - admission.admitted_at).total_seconds() / 86400, 1)
    elif admission.admitted_at:
        from datetime import datetime

        length_of_stay = round((datetime.utcnow() - admission.admitted_at).total_seconds() / 86400, 1)
    return AdmissionResponse(
        id=admission.id,
        clinic_id=admission.clinic_id,
        patient_id=admission.patient_id,
        consultation_id=admission.consultation_id,
        admission_number=admission.admission_number,
        status=admission.status,
        reason=admission.reason,
        diagnosis_summary=admission.diagnosis_summary,
        outcome=getattr(admission, "outcome", None),
        attending_clinician_user_id=getattr(admission, "attending_clinician_user_id", None),
        attending_clinician_name=attending_name,
        length_of_stay_days=length_of_stay,
        notes=admission.notes,
        admitted_at=admission.admitted_at,
        discharged_at=admission.discharged_at,
        patient_name=patient_name,
        current_bed=current_bed,
        stays=stays_out,
    )


def _room_response(room: models.HospitalRoom) -> HospitalRoomResponse:
    beds = room.beds or []
    return HospitalRoomResponse(
        id=room.id,
        clinic_id=room.clinic_id,
        ward_name=room.ward_name,
        room_number=room.room_number,
        room_type=room.room_type,
        capacity=room.capacity,
        status=room.status,
        notes=room.notes,
        bed_count=len(beds),
        occupied_beds=sum(1 for b in beds if b.status == "occupied"),
    )


@router.get("/dashboard", response_model=HospitalizationDashboardStats)
def hospitalization_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return HospitalizationService.dashboard_stats(db, clinic_id=clinic.id)


@router.get("/reports/monthly")
def hospitalization_monthly_report(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES)
    from datetime import date

    today = date.today()
    clinic = resolve_clinic_for_user(db, current_user)
    return HospitalizationService.monthly_report(
        db, clinic_id=clinic.id, year=year or today.year, month=month or today.month
    )


@router.get("/occupancy", response_model=OccupancySummary)
def occupancy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES + ("lab_technician", "pharmacist",))
    clinic = resolve_clinic_for_user(db, current_user)
    return HospitalizationService.occupancy_summary(db, clinic_id=clinic.id)


@router.get("/rooms", response_model=List[HospitalRoomResponse])
def list_rooms(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES + BED_ADMIN_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    rooms = HospitalizationService.list_rooms(db, clinic_id=clinic.id)
    return [_room_response(r) for r in rooms]


@router.post("/rooms", response_model=HospitalRoomResponse, status_code=201)
def create_room(
    payload: HospitalRoomCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ("platform_admin", "clinic_admin", "admin"))
    clinic = resolve_clinic_for_user(db, current_user)
    room = HospitalizationService.create_room(
        db,
        clinic_id=clinic.id,
        payload=payload,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return _room_response(room)


@router.get("/beds", response_model=List[HospitalBedResponse])
def list_beds(
    room_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES + BED_ADMIN_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    beds = HospitalizationService.list_beds(db, clinic_id=clinic.id, room_id=room_id)
    return [_bed_response(b) for b in beds]


@router.post("/rooms/{room_id}/beds", response_model=HospitalBedResponse, status_code=201)
def add_bed(
    room_id: int,
    payload: HospitalBedCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ("platform_admin", "clinic_admin", "admin"))
    clinic = resolve_clinic_for_user(db, current_user)
    bed = HospitalizationService.add_bed(
        db,
        clinic_id=clinic.id,
        room_id=room_id,
        payload=payload,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return _bed_response(bed)


@router.patch("/rooms/{room_id}", response_model=HospitalRoomResponse)
def update_room(
    room_id: int,
    payload: HospitalRoomUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, BED_ADMIN_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    room = HospitalizationService.update_room(
        db,
        clinic_id=clinic.id,
        room_id=room_id,
        status=payload.status,
        notes=payload.notes,
        room_type=payload.room_type,
    )
    return _room_response(room)


@router.patch("/beds/{bed_id}", response_model=HospitalBedResponse)
def update_bed(
    bed_id: int,
    payload: HospitalBedUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, BED_ADMIN_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    bed = HospitalizationService.update_bed(
        db, clinic_id=clinic.id, bed_id=bed_id, status=payload.status
    )
    return _bed_response(bed)


@router.get("/admissions", response_model=List[AdmissionResponse])
def list_admissions(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    admissions = HospitalizationService.list_admissions(db, clinic_id=clinic.id, status=status)
    return [_admission_response(a) for a in admissions]


@router.post("/admissions", response_model=AdmissionResponse, status_code=201)
def create_admission(
    payload: AdmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    admission = HospitalizationService.admit_patient(
        db,
        clinic_id=clinic.id,
        payload=payload,
        actor=current_user,
        client_ip=client_ip(request),
    )
    db.refresh(admission)
    return _admission_response(admission)


@router.get("/admissions/{admission_id}", response_model=AdmissionResponse)
def get_admission(
    admission_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    admission = HospitalizationService._get_admission(db, clinic.id, admission_id)
    return _admission_response(admission)


@router.patch("/admissions/{admission_id}/status", response_model=AdmissionResponse)
def update_admission_status(
    admission_id: int,
    payload: AdmissionStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    admission = HospitalizationService.update_status(
        db,
        clinic_id=clinic.id,
        admission_id=admission_id,
        payload=payload,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return _admission_response(admission)


@router.post("/admissions/{admission_id}/assign-bed", response_model=AdmissionResponse)
def assign_bed(
    admission_id: int,
    payload: BedAssignmentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, ADMISSION_ROLES + BED_ADMIN_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    admission = HospitalizationService.assign_bed(
        db,
        clinic_id=clinic.id,
        admission_id=admission_id,
        payload=payload,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return _admission_response(admission)
