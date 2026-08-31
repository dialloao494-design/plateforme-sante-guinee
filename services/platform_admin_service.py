"""Platform administration queries with explicit tenant and safety semantics."""

from __future__ import annotations

import json
import os
import re
from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

import models
from models.clinic_node_ops import ClinicNodeBackupRecord, ClinicNodeHeartbeat, SyncConflict, SyncOutboxEvent
from models.refresh_token import RefreshToken
from schemas.platform import PlatformAccount


TEST_EMAIL_PATTERNS = (
    re.compile(r"@(sante-gn\.test|pilot\.local|clinic\.test|patient\.gn|aasma-clinic\.gn|field\.local)$", re.I),
    re.compile(r"(^|[.+_-])(test|testing|e2e|stress|staging|demo|fake|sample|probe|verify|prodtest|pwtest)([.+_@-]|$)", re.I),
)
TECHNICAL_EMAIL_PATTERNS = (
    re.compile(r"(^|[.+_-])(service|system|sync|robot|automation|monitor|backup)([.+_@-]|$)", re.I),
)


def classify_account(user: models.User) -> tuple[str, list[str]]:
    email = (user.email or "").strip().lower()
    if user.role in ("platform_owner", "platform_admin"):
        return "technical", ["Compte d’administration de la plateforme"]
    for pattern in TEST_EMAIL_PATTERNS:
        if pattern.search(email):
            return "test", ["Adresse correspondant aux conventions de test"]
    for pattern in TECHNICAL_EMAIL_PATTERNS:
        if pattern.search(email):
            return "technical", ["Adresse de service ou d’automatisation"]
    if user.clinic_id is not None:
        return "production", ["Compte rattaché à une clinique"]
    return "unknown", ["Aucune clinique ni convention technique reconnue"]


def _active_sessions(db: Session, user_id: int) -> int:
    return db.query(RefreshToken).filter(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
        RefreshToken.expires_at > datetime.utcnow(),
    ).count()


def _can_delete(db: Session, user: models.User) -> bool:
    if user.is_active or user.role in ("platform_owner", "platform_admin"):
        return False
    pending = db.query(models.StaffActivationToken.id).filter(
        models.StaffActivationToken.user_id == user.id,
        models.StaffActivationToken.used_at.is_(None),
    ).first()
    authored = db.query(models.ClinicalAuditLog.id).filter(models.ClinicalAuditLog.actor_id == user.id).first()
    return bool(pending and not authored and user.last_login_at is None and user.email_verified_at is None)


def list_accounts(db: Session, *, category: str | None = None, clinic_id: int | None = None, role: str | None = None, search: str | None = None) -> list[PlatformAccount]:
    q = db.query(models.User)
    if clinic_id is not None:
        q = q.filter(models.User.clinic_id == clinic_id)
    if role:
        q = q.filter(models.User.role == role)
    if search:
        q = q.filter(models.User.email.ilike(f"%{search.strip()}%"))
    clinics = {c.id: c.name for c in db.query(models.Clinic.id, models.Clinic.name).all()}
    rows = []
    for user in q.order_by(models.User.email).all():
        bucket, reasons = classify_account(user)
        if category and category != "all" and bucket != category:
            continue
        rows.append(PlatformAccount(
            id=user.id, email=user.email, role=user.role, clinic_id=user.clinic_id,
            clinic_name=clinics.get(user.clinic_id), category=bucket,
            classification_reasons=reasons, is_active=user.is_active,
            created_at=getattr(user, "created_at", None), last_login_at=user.last_login_at,
            mfa_enabled=bool(user.mfa_enabled), failed_login_attempts=user.failed_login_attempts or 0,
            locked_until=user.locked_until, active_sessions=_active_sessions(db, user.id),
            can_delete=_can_delete(db, user),
        ))
    return rows


def clinic_configuration(clinic: models.Clinic) -> dict:
    try:
        stored = json.loads(clinic.configuration_json or "{}")
    except (TypeError, ValueError):
        stored = {}
    return {
        "enabled_modules": stored.get("enabled_modules", ["reception", "billing", "doctor", "nursing", "laboratory", "pharmacy"]),
        "payment_methods": stored.get("payment_methods", ["cash", "orange_money", "bank_transfer", "insurance"]),
        "receipt_template": stored.get("receipt_template", "aasma_standard"),
        "catalogue_version": stored.get("catalogue_version", "current"),
        "offline_workstations_enabled": bool(stored.get("offline_workstations_enabled", True)),
        "offline_data_epoch": int(stored.get("offline_data_epoch", 1)),
        "data_retention_days": int(stored.get("data_retention_days", 3650)),
    }


def clinic_health(db: Session, clinic_id: int) -> dict:
    heartbeat = db.query(ClinicNodeHeartbeat).filter(ClinicNodeHeartbeat.clinic_id == clinic_id).order_by(ClinicNodeHeartbeat.received_at.desc()).first()
    backup = db.query(ClinicNodeBackupRecord).filter(ClinicNodeBackupRecord.clinic_id == clinic_id).order_by(ClinicNodeBackupRecord.created_at.desc()).first()
    open_conflicts = db.query(SyncConflict).filter(SyncConflict.clinic_id == clinic_id, SyncConflict.status == "open").count()
    pending = db.query(SyncOutboxEvent).filter(SyncOutboxEvent.clinic_id == clinic_id, SyncOutboxEvent.status.in_(("pending", "in_flight", "dead"))).count()
    dead = db.query(SyncOutboxEvent).filter(SyncOutboxEvent.clinic_id == clinic_id, SyncOutboxEvent.status == "dead").count()
    return {
        "status": "attention" if open_conflicts or dead else "ok",
        "application_version": os.getenv("RAILWAY_GIT_COMMIT_SHA") or os.getenv("APP_VERSION") or "non renseignée",
        "database": "connected",
        "migration_revision": os.getenv("ALEMBIC_REVISION", "runtime"),
        "sync": {"pending": pending, "dead": dead, "conflicts": open_conflicts, "last_success_at": heartbeat.last_sync_success_at if heartbeat else None},
        "workstation": {"last_seen_at": heartbeat.received_at if heartbeat else None, "software_version": heartbeat.software_version if heartbeat else None, "schema_version": heartbeat.schema_version if heartbeat else None},
        "backup": {"last_at": backup.created_at if backup else None, "verified": bool(backup.verified) if backup else False, "restored_at": backup.restored_at if backup else None},
    }


def data_inventory(db: Session, clinic_id: int) -> dict:
    domains = {
        "patients": models.Patient,
        "appointments": models.RendezVous,
        "admissions": models.Admission,
        "consultations": models.ClinicalConsultation,
        "invoices": models.Invoice,
        "payments": models.PaymentRecord,
        "lab_orders": models.LabOrder,
        "imaging_orders": models.ImagingOrder,
        "prescriptions": models.Prescription,
        "nursing_records": models.NurseAssessment,
    }
    counts = {}
    for label, model in domains.items():
        if hasattr(model, "clinic_id"):
            counts[label] = db.query(func.count(model.id)).filter(model.clinic_id == clinic_id).scalar() or 0
        elif label == "payments":
            invoice_ids = db.query(models.Invoice.id).filter(models.Invoice.clinic_id == clinic_id)
            counts[label] = db.query(func.count(model.id)).filter(model.invoice_id.in_(invoice_ids)).scalar() or 0
    duplicate_groups = db.query(
        func.lower(models.Patient.first_name), func.lower(models.Patient.last_name), models.Patient.phone, func.count(models.Patient.id)
    ).filter(models.Patient.clinic_id == clinic_id).group_by(
        func.lower(models.Patient.first_name), func.lower(models.Patient.last_name), models.Patient.phone
    ).having(func.count(models.Patient.id) > 1).count()
    candidates = []
    duplicate_rows = db.query(
        func.lower(models.Patient.first_name).label("first_name"),
        func.lower(models.Patient.last_name).label("last_name"),
        models.Patient.phone.label("phone"),
    ).filter(models.Patient.clinic_id == clinic_id).group_by(
        func.lower(models.Patient.first_name), func.lower(models.Patient.last_name), models.Patient.phone
    ).having(func.count(models.Patient.id) > 1).limit(50).all()
    for group in duplicate_rows:
        patients = db.query(models.Patient).filter(
            models.Patient.clinic_id == clinic_id,
            func.lower(models.Patient.first_name) == group.first_name,
            func.lower(models.Patient.last_name) == group.last_name,
            models.Patient.phone == group.phone,
        ).order_by(models.Patient.id).all()
        candidates.append({"match": {"first_name": group.first_name, "last_name": group.last_name, "phone": group.phone}, "patients": [{"id": p.id, "patient_number": p.patient_number, "first_name": p.first_name, "last_name": p.last_name, "phone": p.phone, "created_at": p.created_at} for p in patients]})
    return {"clinic_id": clinic_id, "counts": counts, "duplicate_groups": duplicate_groups, "duplicate_candidates": candidates}
