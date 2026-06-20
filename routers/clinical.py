"""Modular clinical information system — REST API."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

import models
from core.clinical_access import (
    ADMIN_ROLES,
    BILLING_PAY_ROLES,
    BILLING_READ_ROLES,
    BILLING_REVENUE_ROLES,
    CLINIC_OPS_ROLES,
    DOCTOR_ROLES,
    LAB_QUEUE_ROLES,
    LAB_ROLES,
    PHARMACY_QUEUE_ROLES,
    PHARMACY_ROLES,
    RECEPTION_ROLES,
    assert_clinic_access,
    assert_role,
    doctor_for_user,
    resolve_clinic_for_user,
    user_clinic_id,
)
from core.http_utils import client_ip
from database import get_db
from schemas.clinical import (
    ChargePaymentRequest,
    ClinicOperationsSummary,
    ClinicChargeResponse,
    ClinicCreate,
    ClinicResponse,
    ClinicalAppointmentCreate,
    ClinicalAppointmentResponse,
    ClinicalAuditLogResponse,
    ConsultationResponse,
    ConsultationStart,
    ConsultationUpdate,
    DailyRevenueSummary,
    LabOrderCreate,
    LabOrderResponse,
    LabOrderStatusUpdate,
    LabResultCreate,
    LabResultResponse,
    PatientIntakeCreate,
    PatientIntakeResponse,
    PatientSearchResponse,
    PharmacyOrderResponse,
    PharmacyStatusUpdate,
    PrescriptionCreate,
    PrescriptionItemBrief,
    PrescriptionResponse,
    StaffCreate,
    StaffResponse,
    StaffRoleUpdate,
)
from schemas.pharmacy_inventory import (
    PharmacyInventoryAdjust,
    PharmacyInventoryItemResponse,
    PharmacyInventoryUpsert,
)
from security import get_current_user
from services.clinical_audit_service import ClinicalAuditService
from services.clinic_operations_service import clinic_operations_summary
from services.clinic_billing_service import ClinicBillingService
from services.clinical_workflow_service import ClinicalWorkflowService
from services.medical_history_service import MedicalHistoryService
from schemas import medical_history as mh_schemas
from services.cis_audit import log_cis_denied
from services.backup_validation_service import default_backup_dir, validate_backup_directory
from services.user_provisioning import EmailAlreadyRegisteredError, create_staff_user
from models.user import User

router = APIRouter(prefix="/clinical", tags=["Clinical CIS"])


def _require_role(
    db: Session,
    user: User,
    allowed: tuple[str, ...],
    request: Request,
    *,
    resource_type: str = "cis",
    clinic_id: int | None = None,
) -> None:
    if user.role in allowed:
        return
    log_cis_denied(
        db,
        actor=user,
        action="access",
        resource_type=resource_type,
        clinic_id=clinic_id,
        client_ip=client_ip(request),
    )
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Requires one of roles: {list(allowed)}",
    )


def _charge_response(charge: models.ClinicCharge) -> ClinicChargeResponse:
    patient_name = None
    if charge.patient:
        patient_name = f"{charge.patient.first_name} {charge.patient.last_name}".strip()
    return ClinicChargeResponse(
        id=charge.id,
        clinic_id=charge.clinic_id,
        patient_id=charge.patient_id,
        charge_type=charge.charge_type,
        source_type=charge.source_type,
        source_id=charge.source_id,
        description=charge.description,
        amount_gnf=charge.amount_gnf,
        payment_status=charge.payment_status,
        payment_method=charge.payment_method,
        paid_at=charge.paid_at,
        created_at=charge.created_at,
        patient_name=patient_name,
    )


def _appointment_response(rdv: models.RendezVous) -> ClinicalAppointmentResponse:
    patient_name = None
    doctor_name = None
    if rdv.patient:
        patient_name = f"{rdv.patient.first_name} {rdv.patient.last_name}".strip()
    if rdv.doctor:
        doctor_name = rdv.doctor.name
    return ClinicalAppointmentResponse(
        id=rdv.id,
        clinic_id=rdv.clinic_id,
        patient_id=rdv.patient_id,
        doctor_id=rdv.doctor_id,
        date=rdv.date,
        duration_minutes=rdv.duration_minutes,
        status=rdv.status,
        clinical_status=rdv.clinical_status,
        consultation_type=rdv.consultation_type,
        patient_name=patient_name,
        doctor_name=doctor_name,
    )


def _consultation_response(c: models.ClinicalConsultation) -> ConsultationResponse:
    patient_name = doctor_name = None
    if c.patient:
        patient_name = f"{c.patient.first_name} {c.patient.last_name}".strip()
    if c.doctor:
        doctor_name = c.doctor.name
    return ConsultationResponse(
        id=c.id,
        clinic_id=c.clinic_id,
        appointment_id=c.appointment_id,
        patient_id=c.patient_id,
        doctor_id=c.doctor_id,
        status=c.status,
        chief_complaint=c.chief_complaint,
        history=c.history,
        examination=c.examination,
        diagnosis=c.diagnosis,
        treatment_plan=c.treatment_plan,
        started_at=c.started_at,
        completed_at=c.completed_at,
        patient_name=patient_name,
        doctor_name=doctor_name,
    )


# --- Admin: clinic & staff ---


@router.post("/clinics", response_model=ClinicResponse, status_code=status.HTTP_201_CREATED)
def create_clinic(
    body: ClinicCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, ("platform_owner", "platform_admin"))
    clinic = models.Clinic(
        name=body.name.strip(),
        address=body.address,
        city=body.city,
        phone=body.phone,
        email=body.email,
        is_active=True,
    )
    db.add(clinic)
    db.commit()
    db.refresh(clinic)
    return clinic


@router.get("/clinics", response_model=List[ClinicResponse])
def list_clinics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role in ("platform_owner", "platform_admin"):
        return db.query(models.Clinic).filter(models.Clinic.is_active.is_(True)).all()
    cid = user_clinic_id(current_user)
    if not cid:
        raise HTTPException(status_code=400, detail="No clinic assigned")
    clinic = db.query(models.Clinic).filter(models.Clinic.id == cid).first()
    return [clinic] if clinic else []


@router.post("/staff", response_model=StaffResponse, status_code=status.HTTP_201_CREATED)
def provision_staff(
    body: StaffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, ("platform_owner", "platform_admin", "clinic_admin", "admin"))
    normalized_role = str(body.role or "").strip().lower()
    clinic_id = body.clinic_id
    if current_user.role in ("clinic_admin", "admin"):
        if normalized_role in ("clinic_admin", "admin", "platform_admin", "platform_owner"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clinic administrators cannot assign platform or clinic-admin roles",
            )
        own_clinic = user_clinic_id(current_user, db)
        if own_clinic is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is not assigned to a clinic",
            )
        if clinic_id != own_clinic:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Clinic administrators can only create staff for their own clinic",
            )
        clinic_id = own_clinic
    assert_clinic_access(current_user, clinic_id)
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    try:
        provisioned = create_staff_user(
            db,
            email=body.email,
            password=body.password,
            role=body.role,
            clinic_id=clinic_id,
            channel="admin_api",
            actor_user_id=current_user.id,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    user = provisioned.user
    return StaffResponse(id=user.id, email=user.email, role=user.role, clinic_id=user.clinic_id, is_active=user.is_active)


@router.get("/staff", response_model=List[StaffResponse])
def list_staff(
    clinic_id: int = Query(...),
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List clinic staff — supports multiple users per role."""
    assert_role(current_user, ("platform_owner", "platform_admin", "clinic_admin", "admin"))
    assert_clinic_access(current_user, clinic_id)
    q = db.query(models.User).filter(models.User.clinic_id == clinic_id)
    if role:
        q = q.filter(models.User.role == role.strip().lower())
    staff_roles = (
        "receptionist",
        "cashier",
        "doctor",
        "lab_technician",
        "pharmacist",
        "nutritionist",
        "midwife",
        "pev_agent",
        "nurse",
        "clinic_admin",
        "admin",
    )
    rows = q.filter(models.User.role.in_(staff_roles)).order_by(models.User.role, models.User.email).all()
    return [
        StaffResponse(id=u.id, email=u.email, role=u.role, clinic_id=u.clinic_id, is_active=u.is_active)
        for u in rows
    ]


@router.patch("/staff/{user_id}/deactivate", response_model=StaffResponse)
def deactivate_staff(
    user_id: int,
    clinic_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, ("platform_owner", "platform_admin", "clinic_admin", "admin"))
    assert_clinic_access(current_user, clinic_id)
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id, models.User.clinic_id == clinic_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Staff member not found")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return StaffResponse(id=user.id, email=user.email, role=user.role, clinic_id=user.clinic_id, is_active=user.is_active)


@router.patch("/staff/{user_id}/role", response_model=StaffResponse)
def update_staff_role(
    user_id: int,
    body: StaffRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from core.roles import CLINICAL_STAFF_ROLES, assert_known_role

    assert_role(current_user, ("platform_owner", "platform_admin", "clinic_admin", "admin"))
    assert_clinic_access(current_user, body.clinic_id)
    normalized = assert_known_role(body.role)
    if normalized not in CLINICAL_STAFF_ROLES:
        raise HTTPException(status_code=400, detail=f"Role '{body.role}' is not a clinical staff role")
    if current_user.role in ("clinic_admin", "admin") and normalized in (
        "clinic_admin",
        "admin",
        "platform_admin",
        "platform_owner",
    ):
        raise HTTPException(status_code=403, detail="Cannot assign privileged roles")
    user = (
        db.query(models.User)
        .filter(models.User.id == user_id, models.User.clinic_id == body.clinic_id)
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Staff member not found")
    from core.provisioning_context import provisioning_channel

    user.role = normalized
    db.add(user)
    with provisioning_channel("admin_api"):
        db.commit()
    db.refresh(user)
    return StaffResponse(id=user.id, email=user.email, role=user.role, clinic_id=user.clinic_id, is_active=user.is_active)


# --- Clinic operations (unified dashboard) ---


@router.get("/operations/summary", response_model=ClinicOperationsSummary)
def operations_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, CLINIC_OPS_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return ClinicOperationsSummary(**clinic_operations_summary(db, clinic_id=clinic.id))


# --- Reception ---


@router.get("/reception/patients", response_model=List[PatientSearchResponse])
def search_patients(
    q: str = Query(..., min_length=2),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, RECEPTION_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return ClinicalWorkflowService.search_patients(db, clinic_id=clinic.id, query=q)


@router.post("/reception/patients", response_model=PatientIntakeResponse, status_code=201)
def intake_patient(
    body: PatientIntakeCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, RECEPTION_ROLES, request, clinic_id=clinic.id)
    patient = ClinicalWorkflowService.register_patient(
        db,
        clinic_id=clinic.id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return patient


@router.post("/reception/appointments", response_model=ClinicalAppointmentResponse, status_code=201)
def create_clinical_appointment(
    body: ClinicalAppointmentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, RECEPTION_ROLES, request, clinic_id=clinic.id)
    rdv = ClinicalWorkflowService.create_appointment(
        db,
        clinic_id=clinic.id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    db.refresh(rdv, ["patient", "doctor"])
    return _appointment_response(rdv)


@router.get("/reception/queue", response_model=List[ClinicalAppointmentResponse])
def reception_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from core.rbac import CASHIER_ROLES, CLINIC_ADMIN_ROLES

    assert_role(current_user, RECEPTION_ROLES + CASHIER_ROLES + CLINIC_ADMIN_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    items = ClinicalWorkflowService.reception_queue(db, clinic_id=clinic.id)
    for item in items:
        db.refresh(item, ["patient", "doctor"])
    return [_appointment_response(i) for i in items]


@router.post("/reception/appointments/{appointment_id}/check-in", response_model=ClinicalAppointmentResponse)
def check_in(
    appointment_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, RECEPTION_ROLES, request, clinic_id=clinic.id)
    rdv = ClinicalWorkflowService.check_in_appointment(
        db,
        appointment_id=appointment_id,
        clinic_id=clinic.id,
        actor=current_user,
        client_ip=client_ip(request),
    )
    db.refresh(rdv, ["patient", "doctor"])
    return _appointment_response(rdv)


@router.get("/reception/doctors")
def clinic_doctors(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, CLINIC_OPS_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    doctors = (
        db.query(models.Doctor)
        .filter(models.Doctor.clinic_id == clinic.id)
        .order_by(models.Doctor.last_name)
        .all()
    )
    return [{"id": d.id, "name": d.name, "specialty": d.specialty} for d in doctors]


@router.get("/reception/follow-ups", response_model=mh_schemas.FollowUpReceptionSummary)
def reception_follow_ups(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, RECEPTION_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return MedicalHistoryService.reception_follow_up_summary(db, clinic_id=clinic.id)


# --- Doctor ---


@router.get("/doctor/queue", response_model=List[ClinicalAppointmentResponse])
def doctor_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, (*DOCTOR_ROLES, *ADMIN_ROLES))
    clinic = resolve_clinic_for_user(db, current_user)
    if current_user.role == "doctor":
        doctor = doctor_for_user(db, current_user)
        items = ClinicalWorkflowService.doctor_queue(
            db, clinic_id=clinic.id, doctor_id=doctor.id
        )
    else:
        items = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.clinic_id == clinic.id,
                models.RendezVous.clinical_status.in_(("checked_in", "in_consultation")),
                models.RendezVous.status != "cancelled",
            )
            .order_by(models.RendezVous.date.asc())
            .all()
        )
    for item in items:
        db.refresh(item, ["patient", "doctor"])
    return [_appointment_response(i) for i in items]


@router.post("/consultations", response_model=ConsultationResponse, status_code=201)
def start_consultation(
    body: ConsultationStart,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, DOCTOR_ROLES, request, clinic_id=clinic.id)
    doctor = doctor_for_user(db, current_user)
    consultation = ClinicalWorkflowService.start_consultation(
        db,
        clinic_id=clinic.id,
        appointment_id=body.appointment_id,
        doctor=doctor,
        chief_complaint=body.chief_complaint,
        actor=current_user,
        client_ip=client_ip(request),
    )
    db.refresh(consultation, ["patient", "doctor"])
    return _consultation_response(consultation)


@router.patch("/consultations/{consultation_id}", response_model=ConsultationResponse)
def update_consultation(
    consultation_id: int,
    body: ConsultationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, DOCTOR_ROLES, request, clinic_id=clinic.id)
    doctor = doctor_for_user(db, current_user)
    consultation = ClinicalWorkflowService.update_consultation(
        db,
        consultation_id=consultation_id,
        clinic_id=clinic.id,
        doctor_id=doctor.id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    db.refresh(consultation, ["patient", "doctor"])
    return _consultation_response(consultation)


@router.post("/consultations/{consultation_id}/lab-orders", response_model=LabOrderResponse, status_code=201)
def order_lab(
    consultation_id: int,
    body: LabOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, DOCTOR_ROLES, request, clinic_id=clinic.id)
    doctor = doctor_for_user(db, current_user)
    order = ClinicalWorkflowService.create_lab_order(
        db,
        clinic_id=clinic.id,
        consultation_id=consultation_id,
        doctor=doctor,
        user=current_user,
        payload=body,
        client_ip=client_ip(request),
    )
    db.refresh(order, ["patient"])
    return LabOrderResponse(
        id=order.id,
        clinic_id=order.clinic_id,
        consultation_id=order.consultation_id,
        patient_id=order.patient_id,
        test_code=order.test_code,
        test_name=order.test_name,
        priority=order.priority,
        status=order.status,
        patient_name=f"{order.patient.first_name} {order.patient.last_name}" if order.patient else None,
    )


@router.post("/consultations/{consultation_id}/prescriptions", response_model=PrescriptionResponse, status_code=201)
def prescribe(
    consultation_id: int,
    body: PrescriptionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, DOCTOR_ROLES, request, clinic_id=clinic.id)
    doctor = doctor_for_user(db, current_user)
    rx = ClinicalWorkflowService.create_prescription(
        db,
        clinic_id=clinic.id,
        consultation_id=consultation_id,
        doctor=doctor,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    db.refresh(rx, ["items", "patient"])
    return PrescriptionResponse(
        id=rx.id,
        clinic_id=rx.clinic_id,
        consultation_id=rx.consultation_id,
        patient_id=rx.patient_id,
        status=rx.status,
        items=[
            {
                "medication_name": i.medication_name,
                "dosage": i.dosage,
                "route": i.route,
                "frequency": i.frequency,
                "duration_days": i.duration_days,
                "quantity": i.quantity,
                "instructions": i.instructions,
            }
            for i in rx.items
        ],
        patient_name=f"{rx.patient.first_name} {rx.patient.last_name}" if rx.patient else None,
    )


@router.post(
    "/consultations/{consultation_id}/vitals",
    response_model=mh_schemas.PatientVitalSignsResponse,
    status_code=201,
)
def record_consultation_vitals(
    consultation_id: int,
    body: mh_schemas.PatientVitalSignsCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, DOCTOR_ROLES, request, clinic_id=clinic.id)
    doctor = doctor_for_user(db, current_user)
    consultation = (
        db.query(models.ClinicalConsultation)
        .filter(
            models.ClinicalConsultation.id == consultation_id,
            models.ClinicalConsultation.clinic_id == clinic.id,
            models.ClinicalConsultation.doctor_id == doctor.id,
            models.ClinicalConsultation.deleted_at.is_(None),
        )
        .first()
    )
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    payload = body.model_copy(update={"consultation_id": consultation_id})
    return MedicalHistoryService.record_vitals(
        db,
        consultation.patient_id,
        payload,
        current_user,
        client_ip=client_ip(request),
    )


@router.post(
    "/consultations/{consultation_id}/follow-ups",
    response_model=mh_schemas.FollowUpScheduleResponse,
    status_code=201,
)
def schedule_consultation_follow_up(
    consultation_id: int,
    body: mh_schemas.FollowUpScheduleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, DOCTOR_ROLES, request, clinic_id=clinic.id)
    doctor = doctor_for_user(db, current_user)
    consultation = (
        db.query(models.ClinicalConsultation)
        .filter(
            models.ClinicalConsultation.id == consultation_id,
            models.ClinicalConsultation.clinic_id == clinic.id,
            models.ClinicalConsultation.doctor_id == doctor.id,
            models.ClinicalConsultation.deleted_at.is_(None),
        )
        .first()
    )
    if not consultation:
        raise HTTPException(status_code=404, detail="Consultation not found")
    fu = MedicalHistoryService.schedule_follow_up(
        db,
        patient_id=consultation.patient_id,
        clinic_id=clinic.id,
        consultation_id=consultation_id,
        doctor_id=doctor.id,
        payload=body,
        current_user=current_user,
        client_ip=client_ip(request),
    )
    db.refresh(fu, ["patient"])
    return mh_schemas.FollowUpScheduleResponse(
        id=fu.id,
        patient_id=fu.patient_id,
        clinic_id=fu.clinic_id,
        consultation_id=fu.consultation_id,
        doctor_id=fu.doctor_id,
        doctor_name=doctor.name,
        patient_name=f"{fu.patient.first_name} {fu.patient.last_name}" if fu.patient else None,
        scheduled_date=fu.scheduled_date,
        interval_type=fu.interval_type,
        visit_type=fu.visit_type,
        reason=fu.reason,
        clinical_notes=fu.clinical_notes,
        status=fu.status,
        follow_up_appointment_id=fu.follow_up_appointment_id,
        created_at=fu.created_at,
    )


# --- Laboratory ---


@router.get("/lab/orders", response_model=List[LabOrderResponse])
def lab_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, LAB_QUEUE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    orders = ClinicalWorkflowService.lab_queue(db, clinic_id=clinic.id)
    out = []
    for order in orders:
        db.refresh(order, ["patient"])
        out.append(
            LabOrderResponse(
                id=order.id,
                clinic_id=order.clinic_id,
                consultation_id=order.consultation_id,
                patient_id=order.patient_id,
                test_code=order.test_code,
                test_name=order.test_name,
                priority=order.priority,
                status=order.status,
                patient_name=f"{order.patient.first_name} {order.patient.last_name}"
                if order.patient
                else None,
            )
        )
    return out


@router.patch("/lab/orders/{order_id}", response_model=LabOrderResponse)
def update_lab_order(
    order_id: int,
    body: LabOrderStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, LAB_ROLES, request, clinic_id=clinic.id)
    order = ClinicalWorkflowService.update_lab_order_status(
        db,
        order_id=order_id,
        clinic_id=clinic.id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    db.refresh(order, ["patient"])
    return LabOrderResponse(
        id=order.id,
        clinic_id=order.clinic_id,
        consultation_id=order.consultation_id,
        patient_id=order.patient_id,
        test_code=order.test_code,
        test_name=order.test_name,
        priority=order.priority,
        status=order.status,
        patient_name=f"{order.patient.first_name} {order.patient.last_name}" if order.patient else None,
    )


@router.post("/lab/orders/{order_id}/results", response_model=LabResultResponse, status_code=201)
def record_lab_result(
    order_id: int,
    body: LabResultCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, LAB_ROLES, request, clinic_id=clinic.id)
    result = ClinicalWorkflowService.record_lab_result(
        db,
        order_id=order_id,
        clinic_id=clinic.id,
        user=current_user,
        payload=body,
        client_ip=client_ip(request),
    )
    return result


@router.post("/lab/results/{result_id}/validate", response_model=LabResultResponse)
def validate_lab_result(
    result_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, LAB_ROLES, request, clinic_id=clinic.id)
    result = ClinicalWorkflowService.validate_lab_result(
        db,
        result_id=result_id,
        clinic_id=clinic.id,
        user=current_user,
        client_ip=client_ip(request),
    )
    return result


@router.get("/lab/results/{result_id}/pdf")
def lab_result_pdf_download(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import Response
    from services.pdf_service import lab_result_pdf

    assert_role(current_user, LAB_ROLES + DOCTOR_ROLES + ADMIN_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    result = (
        db.query(models.LabResult)
        .join(models.LabOrder)
        .filter(models.LabResult.id == result_id, models.LabOrder.clinic_id == clinic.id)
        .first()
    )
    if not result or result.status != "validated":
        raise HTTPException(status_code=404, detail="Validated lab result not found")
    order = result.lab_order
    patient_name = f"{order.patient.first_name} {order.patient.last_name}".strip() if order.patient else "—"
    pdf_bytes = lab_result_pdf(
        patient_name,
        {
            "test_name": order.test_name,
            "test_code": order.test_code,
            "result_summary": result.result_summary,
            "reference_range": result.reference_range,
            "interpretation": result.interpretation,
            "validated_at": str(result.validated_at or ""),
        },
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="lab-result-{result_id}.pdf"'},
    )


# --- Pharmacy ---


def _inventory_response(item: models.PharmacyInventoryItem) -> PharmacyInventoryItemResponse:
    return PharmacyInventoryItemResponse(
        id=item.id,
        clinic_id=item.clinic_id,
        sku=item.sku,
        medication_name=item.medication_name,
        quantity=item.quantity,
        reorder_level=item.reorder_level,
        unit_price_gnf=item.unit_price_gnf,
        low_stock=item.quantity <= item.reorder_level,
        out_of_stock=item.quantity <= 0,
        batch_number=item.batch_number,
        expiry_date=item.expiry_date,
        supplier=item.supplier,
    )


def _serialize_pharmacy_order(order: models.PharmacyOrder, db: Session) -> PharmacyOrderResponse:
    db.refresh(order, ["patient", "prescription"])
    meds = ""
    items: list[PrescriptionItemBrief] = []
    doctor_name = None
    if order.prescription:
        db.refresh(order.prescription, ["items", "prescriber"])
        if order.prescription.items:
            meds = ", ".join(i.medication_name for i in order.prescription.items)
            items = [
                PrescriptionItemBrief(
                    medication_name=i.medication_name,
                    dosage=i.dosage,
                    frequency=i.frequency,
                    quantity=i.quantity,
                    duration_days=i.duration_days,
                    instructions=i.instructions,
                )
                for i in order.prescription.items
            ]
        if order.prescription.prescriber:
            doctor_name = order.prescription.prescriber.name
    prepared_by = None
    if order.prepared_by_user_id:
        user = db.query(models.User).filter(models.User.id == order.prepared_by_user_id).first()
        if user:
            prepared_by = user.email.split("@")[0].replace(".", " ").title()
    return PharmacyOrderResponse(
        id=order.id,
        clinic_id=order.clinic_id,
        prescription_id=order.prescription_id,
        patient_id=order.patient_id,
        status=order.status,
        patient_name=f"{order.patient.first_name} {order.patient.last_name}" if order.patient else None,
        medications=meds,
        doctor_name=doctor_name,
        created_at=order.created_at,
        dispensed_at=order.dispensed_at,
        prepared_by=prepared_by,
        notes=order.notes,
        items=items,
    )


@router.get("/pharmacy/orders", response_model=List[PharmacyOrderResponse])
def pharmacy_queue(
    scope: str = Query("active", pattern="^(active|all|history|dispensed_today)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, PHARMACY_QUEUE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    if scope == "all":
        orders = ClinicalWorkflowService.list_pharmacy_orders(db, clinic_id=clinic.id, scope="all")
    else:
        orders = ClinicalWorkflowService.list_pharmacy_orders(db, clinic_id=clinic.id, scope=scope)
    return [_serialize_pharmacy_order(order, db) for order in orders]


@router.patch("/pharmacy/orders/{order_id}", response_model=PharmacyOrderResponse)
def update_pharmacy_order(
    order_id: int,
    body: PharmacyStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, PHARMACY_ROLES, request, clinic_id=clinic.id)
    order = ClinicalWorkflowService.update_pharmacy_order(
        db,
        order_id=order_id,
        clinic_id=clinic.id,
        user=current_user,
        payload=body,
        client_ip=client_ip(request),
    )
    return _serialize_pharmacy_order(order, db)


@router.get("/pharmacy/inventory", response_model=List[PharmacyInventoryItemResponse])
def pharmacy_inventory_list(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, PHARMACY_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    from services.pharmacy_inventory_service import PharmacyInventoryService

    PharmacyInventoryService.ensure_default_stock(db, clinic_id=clinic.id)
    items = PharmacyInventoryService.list_items(db, clinic_id=clinic.id)
    return [_inventory_response(i) for i in items]


@router.post("/pharmacy/inventory", response_model=PharmacyInventoryItemResponse, status_code=201)
def pharmacy_inventory_upsert(
    body: PharmacyInventoryUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.pharmacy_inventory_service import PharmacyInventoryService

    assert_role(current_user, PHARMACY_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    item = PharmacyInventoryService.upsert_item(
        db,
        clinic_id=clinic.id,
        sku=body.sku,
        medication_name=body.medication_name,
        quantity=body.quantity,
        reorder_level=body.reorder_level,
        unit_price_gnf=body.unit_price_gnf,
        batch_number=body.batch_number,
        expiry_date=body.expiry_date,
        supplier=body.supplier,
    )
    return _inventory_response(item)


@router.patch("/pharmacy/inventory/{item_id}", response_model=PharmacyInventoryItemResponse)
def pharmacy_inventory_adjust(
    item_id: int,
    body: PharmacyInventoryAdjust,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.pharmacy_inventory_service import PharmacyInventoryService

    assert_role(current_user, PHARMACY_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    item = PharmacyInventoryService.adjust_quantity(
        db, clinic_id=clinic.id, item_id=item_id, delta=body.delta
    )
    return _inventory_response(item)


@router.patch("/doctors/{doctor_id}/clinic/{clinic_id}", status_code=status.HTTP_204_NO_CONTENT)
def assign_doctor_to_clinic(
    doctor_id: int,
    clinic_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, ("platform_owner", "platform_admin", "clinic_admin", "admin"))
    doctor = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not doctor or not clinic:
        raise HTTPException(status_code=404, detail="Doctor or clinic not found")
    doctor.clinic_id = clinic_id
    staff_user = db.query(User).filter(User.id == doctor.user_id).first()
    if staff_user:
        staff_user.clinic_id = clinic_id
    db.commit()
    return None


# --- Journey trace ---


@router.get("/patients/{patient_id}/journey")
def patient_journey(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, RECEPTION_ROLES + DOCTOR_ROLES + LAB_ROLES + PHARMACY_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    from core.tenant import assert_patient_in_clinic

    assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic.id)
    return ClinicalWorkflowService.patient_journey(db, clinic_id=clinic.id, patient_id=patient_id)


# --- Audit compliance ---


@router.get("/audit-logs", response_model=List[ClinicalAuditLogResponse])
def list_audit_logs(
    request: Request,
    patient_id: Optional[int] = None,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, CLINIC_OPS_ROLES, request, clinic_id=clinic.id, resource_type="audit_log")
    logs = ClinicalAuditService.list_for_clinic(
        db, clinic_id=clinic.id, patient_id=patient_id, limit=min(limit, 500)
    )
    return logs


# --- Billing ---


@router.get("/billing/charges/pending", response_model=List[ClinicChargeResponse])
def list_pending_charges(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, BILLING_READ_ROLES, request, clinic_id=clinic.id, resource_type="billing")
    charges = ClinicBillingService.pending_charges(db, clinic_id=clinic.id)
    for c in charges:
        db.refresh(c, ["patient"])
    return [_charge_response(c) for c in charges]


@router.post("/billing/charges/{charge_id}/pay", response_model=ClinicChargeResponse)
def pay_charge(
    charge_id: int,
    body: ChargePaymentRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, BILLING_PAY_ROLES, request, clinic_id=clinic.id, resource_type="billing")
    charge = ClinicBillingService.record_payment(
        db,
        charge_id=charge_id,
        clinic_id=clinic.id,
        user=current_user,
        payment_method=body.payment_method,
    )
    from services.cis_audit import log_cis

    log_cis(
        db,
        actor=current_user,
        clinic_id=clinic.id,
        patient_id=charge.patient_id,
        action="update",
        resource_type="billing_payment",
        resource_id=charge.id,
        client_ip=client_ip(request),
    )
    db.refresh(charge, ["patient"])
    return _charge_response(charge)


@router.get("/billing/revenue/daily", response_model=DailyRevenueSummary)
def daily_revenue(
    request: Request,
    day: Optional[date] = Query(None, description="Jour comptable (YYYY-MM-DD), défaut = aujourd'hui"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    clinic = resolve_clinic_for_user(db, current_user)
    _require_role(db, current_user, BILLING_REVENUE_ROLES, request, clinic_id=clinic.id, resource_type="billing")
    summary = ClinicBillingService.daily_summary(db, clinic_id=clinic.id, day=day)
    return DailyRevenueSummary(**summary)


# --- Backup validation ---


@router.get("/admin/backup-status")
def backup_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, ADMIN_ROLES)
