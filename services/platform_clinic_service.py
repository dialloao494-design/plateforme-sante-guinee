"""Platform owner clinic directory — stats, classification, and search."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

import models
from models.refresh_token import RefreshToken
from services.platform_admin_service import clinic_configuration
from core.clinic_classification import classify_clinic
from schemas.platform import (
    PlatformClinicDetail,
    PlatformClinicSummary,
    PlatformModuleUsage,
    PlatformOwnerSummary,
    PlatformRoleBreakdown,
    PlatformStaffMember,
)

STAFF_ROLES = (
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

ROLE_LABELS = {
    "receptionist": "Réception",
    "cashier": "Caisse",
    "doctor": "Médecins",
    "lab_technician": "Laboratoire",
    "pharmacist": "Pharmacie",
    "nutritionist": "Nutrition",
    "midwife": "Sage-femme",
    "pev_agent": "PEV",
    "nurse": "Soins infirmiers",
    "clinic_admin": "Admin clinique",
    "admin": "Admin",
}


def _month_start() -> datetime:
    now = datetime.utcnow()
    return datetime(now.year, now.month, 1)


def _clinic_staff_user_ids_subquery(db: Session, clinic_id: int):
    linked = select(models.ClinicStaff.user_id).where(
        models.ClinicStaff.clinic_id == clinic_id,
        models.ClinicStaff.is_active.is_(True),
    )
    return or_(
        models.User.clinic_id == clinic_id,
        models.User.id.in_(linked),
    )


def _clinic_staff_query(db: Session, clinic_id: int):
    return db.query(models.User).filter(
        _clinic_staff_user_ids_subquery(db, clinic_id),
        models.User.role.in_(STAFF_ROLES),
    )


def _clinic_staff_emails(db: Session, clinic_id: int) -> list[str]:
    rows = _clinic_staff_query(db, clinic_id).with_entities(models.User.email).all()
    return [r[0] for r in rows if r[0]]


def _clinic_admin(db: Session, clinic_id: int) -> models.User | None:
    return (
        _clinic_staff_query(db, clinic_id)
        .filter(
            models.User.role.in_(("clinic_admin", "admin")),
            models.User.is_active.is_(True),
        )
        .order_by(models.User.id)
        .first()
    )


def _last_activity_at(db: Session, clinic_id: int) -> datetime | None:
    candidates: list[datetime | None] = []

    patient_ts = (
        db.query(func.max(models.Patient.updated_at))
        .filter(models.Patient.clinic_id == clinic_id, models.Patient.is_archived.is_(False))
        .scalar()
    )
    candidates.append(patient_ts)

    consult_ts = (
        db.query(func.max(models.ClinicalConsultation.updated_at))
        .filter(
            models.ClinicalConsultation.clinic_id == clinic_id,
            models.ClinicalConsultation.deleted_at.is_(None),
        )
        .scalar()
    )
    candidates.append(consult_ts)

    audit_ts = (
        db.query(func.max(models.ClinicalAuditLog.timestamp))
        .filter(models.ClinicalAuditLog.clinic_id == clinic_id)
        .scalar()
    )
    candidates.append(audit_ts)

    valid = [ts for ts in candidates if ts is not None]
    return max(valid) if valid else None


def _user_last_activity(db: Session, user_id: int) -> datetime | None:
    return (
        db.query(func.max(models.ClinicalAuditLog.timestamp))
        .filter(models.ClinicalAuditLog.actor_id == user_id)
        .scalar()
    )


def _staff_display(db: Session, user: models.User) -> tuple[str | None, str | None]:
    if user.role == "doctor" and user.doctor_profile:
        doc = user.doctor_profile
        return doc.full_name, doc.phone
    return None, None


def _clinic_stats(db: Session, clinic_id: int) -> dict:
    staff_count = _clinic_staff_query(db, clinic_id).count()
    patient_count = (
        db.query(func.count(models.Patient.id))
        .filter(models.Patient.clinic_id == clinic_id, models.Patient.is_archived.is_(False))
        .scalar()
        or 0
    )
    consultation_count = (
        db.query(func.count(models.ClinicalConsultation.id))
        .filter(
            models.ClinicalConsultation.clinic_id == clinic_id,
            models.ClinicalConsultation.deleted_at.is_(None),
        )
        .scalar()
        or 0
    )
    monthly_consultations = (
        db.query(func.count(models.ClinicalConsultation.id))
        .filter(
            models.ClinicalConsultation.clinic_id == clinic_id,
            models.ClinicalConsultation.deleted_at.is_(None),
            models.ClinicalConsultation.created_at >= _month_start(),
        )
        .scalar()
        or 0
    )
    return {
        "staff_count": staff_count,
        "patient_count": patient_count,
        "consultation_count": consultation_count,
        "monthly_consultations": monthly_consultations,
        "last_activity_at": _last_activity_at(db, clinic_id),
    }


def _module_usage(db: Session, clinic_id: int) -> PlatformModuleUsage:
    return PlatformModuleUsage(
        consultations=(
            db.query(func.count(models.ClinicalConsultation.id))
            .filter(
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.deleted_at.is_(None),
            )
            .scalar()
            or 0
        ),
        laboratory=(
            db.query(func.count(models.LabOrder.id))
            .filter(models.LabOrder.clinic_id == clinic_id)
            .scalar()
            or 0
        ),
        pharmacy=(
            db.query(func.count(models.PharmacyOrder.id))
            .filter(models.PharmacyOrder.clinic_id == clinic_id)
            .scalar()
            or 0
        ),
        pev=(
            db.query(func.count(models.ImmunizationRecord.id))
            .filter(models.ImmunizationRecord.clinic_id == clinic_id)
            .scalar()
            or 0
        ),
        nutrition=(
            db.query(func.count(models.NutritionAssessment.id))
            .filter(models.NutritionAssessment.clinic_id == clinic_id)
            .scalar()
            or 0
        ),
        nursing=(
            db.query(func.count(models.NursingProcedure.id))
            .filter(models.NursingProcedure.clinic_id == clinic_id)
            .scalar()
            or 0
        ),
        hospitalization=(
            db.query(func.count(models.Admission.id))
            .filter(models.Admission.clinic_id == clinic_id)
            .scalar()
            or 0
        ),
    )


def _role_breakdown(db: Session, clinic_id: int) -> list[PlatformRoleBreakdown]:
    rows = (
        _clinic_staff_query(db, clinic_id)
        .with_entities(models.User.role, func.count(models.User.id))
        .group_by(models.User.role)
        .all()
    )
    breakdown = []
    for role, count in sorted(rows, key=lambda item: (-item[1], item[0])):
        breakdown.append(
            PlatformRoleBreakdown(
                role=role,
                label=ROLE_LABELS.get(role, role),
                count=count,
            )
        )
    return breakdown


def _status_label(is_active: bool) -> str:
    return "Active" if is_active else "Archived"


def _build_clinic_summary(db: Session, clinic: models.Clinic) -> PlatformClinicSummary:
    stats = _clinic_stats(db, clinic.id)
    staff_emails = _clinic_staff_emails(db, clinic.id)
    category = classify_clinic(
        name=clinic.name,
        is_active=clinic.is_active,
        staff_emails=staff_emails,
        patient_count=stats["patient_count"],
    )
    admin = _clinic_admin(db, clinic.id)
    return PlatformClinicSummary(
        id=clinic.id,
        name=clinic.name,
        city=clinic.city,
        is_active=clinic.is_active,
        status=_status_label(clinic.is_active),
        category=category,
        created_at=clinic.created_at,
        staff_count=stats["staff_count"],
        patient_count=stats["patient_count"],
        consultation_count=stats["consultation_count"],
        last_activity_at=stats["last_activity_at"],
        admin_email=admin.email if admin else None,
    )


def list_clinic_directory(
    db: Session,
    *,
    category: str = "production",
    search: str | None = None,
) -> list[PlatformClinicSummary]:
    clinics = db.query(models.Clinic).order_by(models.Clinic.name).all()
    summaries = [_build_clinic_summary(db, clinic) for clinic in clinics]

    if category and category != "all":
        summaries = [s for s in summaries if s.category == category]

    if search:
        q = search.strip().lower()
        if q:
            filtered: list[PlatformClinicSummary] = []
            for item in summaries:
                if q in item.name.lower():
                    filtered.append(item)
                    continue
                if q == str(item.id):
                    filtered.append(item)
                    continue
                if item.city and q in item.city.lower():
                    filtered.append(item)
                    continue
                if item.admin_email and q in item.admin_email.lower():
                    filtered.append(item)
            summaries = filtered

    return summaries


def get_platform_summary(db: Session, *, category: str = "production") -> PlatformOwnerSummary:
    summaries = list_clinic_directory(db, category=category, search=None)
    active = [s for s in summaries if s.is_active]
    return PlatformOwnerSummary(
        total_clinics=len(summaries),
        active_clinics=len(active),
        total_staff=sum(s.staff_count for s in summaries),
        total_patients=sum(s.patient_count for s in summaries),
        monthly_consultations=sum(
            _clinic_stats(db, s.id)["monthly_consultations"] for s in summaries
        ),
    )


def get_clinic_detail(db: Session, clinic_id: int) -> PlatformClinicDetail | None:
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic:
        return None

    stats = _clinic_stats(db, clinic.id)
    staff_emails = _clinic_staff_emails(db, clinic.id)
    category = classify_clinic(
        name=clinic.name,
        is_active=clinic.is_active,
        staff_emails=staff_emails,
        patient_count=stats["patient_count"],
    )
    admin = _clinic_admin(db, clinic.id)
    admin_name, _ = _staff_display(db, admin) if admin else (None, None)

    return PlatformClinicDetail(
        id=clinic.id,
        name=clinic.name,
        address=clinic.address,
        city=clinic.city,
        phone=clinic.phone,
        email=clinic.email,
        is_active=clinic.is_active,
        status=_status_label(clinic.is_active),
        category=category,
        created_at=clinic.created_at,
        admin_email=admin.email if admin else None,
        admin_name=admin_name,
        staff_count=stats["staff_count"],
        patient_count=stats["patient_count"],
        consultation_count=stats["consultation_count"],
        monthly_consultations=stats["monthly_consultations"],
        last_activity_at=stats["last_activity_at"],
        role_breakdown=_role_breakdown(db, clinic.id),
        module_usage=_module_usage(db, clinic.id),
        suspended_at=clinic.suspended_at,
        suspension_reason=clinic.suspension_reason,
        archived_at=clinic.archived_at,
        configuration=clinic_configuration(clinic),
    )


def list_clinic_staff(db: Session, clinic_id: int) -> list[PlatformStaffMember]:
    users = (
        _clinic_staff_query(db, clinic_id)
        .order_by(models.User.role, models.User.email)
        .all()
    )
    members: list[PlatformStaffMember] = []
    for user in users:
        full_name, phone = _staff_display(db, user)
        latest_invitation = db.query(models.StaffActivationToken).filter(
            models.StaffActivationToken.user_id == user.id,
        ).order_by(models.StaffActivationToken.created_at.desc()).first()
        active_sessions = db.query(RefreshToken).filter(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > datetime.utcnow(),
        ).count()
        last_reset = db.query(func.max(models.PasswordResetToken.created_at)).filter(
            models.PasswordResetToken.user_id == user.id,
        ).scalar()
        members.append(
            PlatformStaffMember(
                id=user.id,
                email=user.email,
                full_name=full_name,
                role=user.role,
                phone=phone,
                is_active=user.is_active,
                last_activity_at=_user_last_activity(db, user.id),
                created_at=getattr(user, "created_at", None),
                last_login_at=user.last_login_at,
                mfa_enabled=bool(user.mfa_enabled),
                failed_login_attempts=user.failed_login_attempts or 0,
                locked_until=user.locked_until,
                invitation_status=(latest_invitation.delivery_status if latest_invitation and latest_invitation.used_at is None and user.last_login_at is None else None),
                invitation_expires_at=(latest_invitation.expires_at if latest_invitation and latest_invitation.used_at is None and user.last_login_at is None else None),
                active_sessions=active_sessions,
                last_password_reset_at=last_reset,
            )
        )
    return members
