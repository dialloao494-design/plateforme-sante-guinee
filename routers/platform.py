"""Platform Owner API — full platform administration (owner role only)."""

from __future__ import annotations

from typing import List, Optional
from datetime import datetime, timedelta
import csv
import io
import json

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
from models.clinic_node_ops import ClinicNodeBackupRecord
from models.refresh_token import RefreshToken
import schemas
from schemas.clinical import ClinicResponse, StaffProfileUpdate
from schemas.platform import (
    PlatformClinicDetail,
    PlatformClinicSummary,
    PlatformOwnerSummary,
    PlatformStaffMember,
    PlatformStaffPasswordReset,
    PlatformLifecycleRequest,
    PlatformAccount,
    PlatformClinicConfigurationUpdate,
    PlatformClinicStateRequest,
    PlatformDataResetRequest,
    PlatformPatientMergeRequest,
    PlatformSession,
)
from database import get_db
from security import get_current_platform_admin, get_current_platform_owner, hash_password, validate_password
from services.platform_clinic_service import (
    get_clinic_detail,
    get_platform_summary,
    list_clinic_directory,
    list_clinic_staff,
)
from services.user_provisioning import (
    EmailAlreadyRegisteredError,
    UserProvisioningError,
    create_clinic_admin_user,
)
from services.user_service import UserService
from services.staff_lifecycle_service import (
    StaffLifecycleError,
    deactivate_staff as lifecycle_deactivate_staff,
    reactivate_staff as lifecycle_reactivate_staff,
    delete_unused_staff as lifecycle_delete_unused_staff,
    revoke_sessions as lifecycle_revoke_sessions,
    update_staff_profile as lifecycle_update_staff_profile,
)
from services.platform_admin_service import list_accounts, clinic_configuration, clinic_health, data_inventory
from services.clinical_audit_service import ClinicalAuditService
from services.auth_session_service import revoke_all_user_refresh_tokens
from services.password_reset_service import create_reset_token, send_reset_email
from core.http_utils import client_ip

router = APIRouter(prefix="/platform", tags=["Platform Owner"])


class ClinicAdminCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: str
    password: str
    clinic_id: int

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserStatusUpdate(BaseModel):
    is_active: bool
    reason: Optional[str] = None


class AccountBulkRequest(BaseModel):
    user_ids: list[int]
    action: str
    reason: str
    execute: bool = False


class PlatformSettingsResponse(BaseModel):
    environment: str
    subscription_billing: str = "coming_soon"
    deployment_admin: str = "coming_soon"


@router.get("/settings", response_model=PlatformSettingsResponse)
def platform_settings(current_user=Depends(get_current_platform_owner)):
    import os

    return PlatformSettingsResponse(environment=os.getenv("ENVIRONMENT", "development"))


@router.get("/summary", response_model=PlatformOwnerSummary)
def platform_summary(
    category: str = Query("production", pattern="^(production|demo|test|archived|all)$"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_admin),
):
    return get_platform_summary(db, category=category)


@router.get("/clinics/directory", response_model=List[PlatformClinicSummary])
def clinic_directory(
    category: str = Query("production", pattern="^(production|demo|test|archived|all)$"),
    search: Optional[str] = Query(None, min_length=1, max_length=128),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_admin),
):
    return list_clinic_directory(db, category=category, search=search)


@router.get("/clinics/{clinic_id}/detail", response_model=PlatformClinicDetail)
def clinic_detail(
    clinic_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_admin),
):
    detail = get_clinic_detail(db, clinic_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return detail


@router.get("/clinics/{clinic_id}/staff", response_model=List[PlatformStaffMember])
def clinic_staff(
    clinic_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_admin),
):
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return list_clinic_staff(db, clinic_id)


@router.get("/clinics/{clinic_id}/demo-patients")
def preview_demo_patients(
    clinic_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_admin),
):
    """Preview synthetic demo/test patients matching safe name patterns."""
    from services.demo_patient_cleanup import cleanup_demo_patients

    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    return cleanup_demo_patients(db, clinic_id, execute=False)


@router.post("/clinics/{clinic_id}/cleanup-demo-patients")
def cleanup_demo_patients_endpoint(
    clinic_id: int,
    execute: bool = Query(False, description="If false, dry-run preview only"),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_admin),
):
    """Delete only obvious demo/E2E patients. Never touches pharmacy stock or staff."""
    from services.demo_patient_cleanup import cleanup_demo_patients

    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    try:
        result = cleanup_demo_patients(db, clinic_id, execute=execute)
    except Exception as exc:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Cleanup failed: {exc}") from exc
    if execute and result.get("failures"):
        result["partial"] = True
    return result


@router.post("/clinics/{clinic_id}/staff/{user_id}/reset-password")
def reset_clinic_staff_password(
    clinic_id: int,
    user_id: int,
    body: PlatformStaffPasswordReset,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_admin),
):
    user = (
        db.query(models.User)
        .filter(
            models.User.id == user_id,
            or_(
                models.User.clinic_id == clinic_id,
                models.User.id.in_(
                    db.query(models.ClinicStaff.user_id).filter(
                        models.ClinicStaff.clinic_id == clinic_id,
                        models.ClinicStaff.is_active.is_(True),
                    )
                ),
            ),
        )
        .first()
    )
    if not user:
        raise HTTPException(status_code=404, detail="Staff member not found")
    if user.role in ("platform_owner", "platform_admin"):
        raise HTTPException(status_code=400, detail="Cannot reset password for platform accounts")
    validate_password(body.new_password)
    user.hashed_password = hash_password(body.new_password)
    user.session_version = int(user.session_version or 0) + 1
    user.must_change_password = False
    # Staff resets must immediately restore clinic access after lockouts from
    # failed attempts (common when Safari cookie auth silently failed).
    if hasattr(user, "failed_login_attempts"):
        user.failed_login_attempts = 0
    if hasattr(user, "locked_until"):
        user.locked_until = None
    db.commit()
    return {"id": user.id, "email": user.email, "reset": True}


@router.get("/clinics", response_model=List[ClinicResponse])
def list_all_clinics(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_owner),
):
    return db.query(models.Clinic).order_by(models.Clinic.name).all()


@router.patch("/clinics/{clinic_id}/active")
def set_clinic_active(
    clinic_id: int,
    body: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_owner),
):
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    clinic.is_active = body.is_active
    db.commit()
    return {"id": clinic.id, "is_active": clinic.is_active}


@router.get("/users", response_model=List[schemas.UserResponse])
def list_all_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_owner),
):
    return UserService.list_users(db)


@router.get("/accounts", response_model=List[PlatformAccount])
def platform_accounts(
    category: Optional[str] = Query(None, pattern="^(production|test|technical|unknown|all)$"),
    clinic_id: Optional[int] = None,
    role: Optional[str] = None,
    search: Optional[str] = Query(None, max_length=128),
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_admin),
):
    return list_accounts(db, category=category, clinic_id=clinic_id, role=role, search=search)


def _lifecycle_error(exc: StaffLifecycleError):
    raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc


@router.patch("/clinics/{clinic_id}/staff/{user_id}", response_model=PlatformStaffMember)
def platform_update_staff(
    clinic_id: int, user_id: int, body: StaffProfileUpdate, request: Request,
    db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin),
):
    if body.clinic_id != clinic_id:
        raise HTTPException(status_code=422, detail="La clinique indiquée ne correspond pas à cette fiche.")
    try:
        lifecycle_update_staff_profile(
            db, clinic_id=clinic_id, user_id=user_id, actor=current_user,
            first_name=body.first_name, last_name=body.last_name, role=body.role,
            reason=body.reason, allow_admin_role=True, ip=client_ip(request),
            user_agent=request.headers.get("user-agent"),
        )
    except StaffLifecycleError as exc:
        _lifecycle_error(exc)
    return next(member for member in list_clinic_staff(db, clinic_id) if member.id == user_id)


@router.patch("/clinics/{clinic_id}/staff/{user_id}/deactivate", response_model=PlatformStaffMember)
def platform_deactivate_staff(clinic_id: int, user_id: int, body: PlatformLifecycleRequest, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    try:
        lifecycle_deactivate_staff(db, clinic_id=clinic_id, user_id=user_id, actor=current_user, reason=body.reason, ip=client_ip(request), user_agent=request.headers.get("user-agent"))
    except StaffLifecycleError as exc:
        _lifecycle_error(exc)
    return next(member for member in list_clinic_staff(db, clinic_id) if member.id == user_id)


@router.patch("/clinics/{clinic_id}/staff/{user_id}/reactivate", response_model=PlatformStaffMember)
def platform_reactivate_staff(clinic_id: int, user_id: int, body: PlatformLifecycleRequest, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    try:
        lifecycle_reactivate_staff(db, clinic_id=clinic_id, user_id=user_id, actor=current_user, reason=body.reason, ip=client_ip(request), user_agent=request.headers.get("user-agent"))
    except StaffLifecycleError as exc:
        _lifecycle_error(exc)
    return next(member for member in list_clinic_staff(db, clinic_id) if member.id == user_id)


@router.delete("/clinics/{clinic_id}/staff/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def platform_delete_staff(clinic_id: int, user_id: int, body: PlatformLifecycleRequest, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    try:
        lifecycle_delete_unused_staff(db, clinic_id=clinic_id, user_id=user_id, actor=current_user, reason=body.reason, ip=client_ip(request), user_agent=request.headers.get("user-agent"))
    except StaffLifecycleError as exc:
        _lifecycle_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/clinics/{clinic_id}/staff/{user_id}/sessions/revoke")
def platform_revoke_staff_sessions(clinic_id: int, user_id: int, body: PlatformLifecycleRequest, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    try:
        count = lifecycle_revoke_sessions(db, clinic_id=clinic_id, user_id=user_id, actor=current_user, reason=body.reason, ip=client_ip(request), user_agent=request.headers.get("user-agent"))
    except StaffLifecycleError as exc:
        _lifecycle_error(exc)
    return {"id": user_id, "revoked_sessions": count}


@router.get("/clinics/{clinic_id}/staff/{user_id}/sessions", response_model=list[PlatformSession])
def platform_staff_sessions(clinic_id: int, user_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    user = db.query(models.User.id).filter(models.User.id == user_id, models.User.clinic_id == clinic_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Membre du personnel introuvable.")
    now = datetime.utcnow()
    return [PlatformSession(id=row.id, created_at=row.created_at, expires_at=row.expires_at,
            ip_address=row.ip_address, user_agent=row.user_agent)
            for row in db.query(RefreshToken).filter(RefreshToken.user_id == user_id,
                RefreshToken.revoked_at.is_(None), RefreshToken.expires_at > now)
            .order_by(RefreshToken.created_at.desc()).all()]


@router.post("/clinics/{clinic_id}/staff/{user_id}/password-reset-link")
def platform_staff_reset_link(clinic_id: int, user_id: int, body: PlatformLifecycleRequest, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    user = db.query(models.User).filter(models.User.id == user_id, models.User.clinic_id == clinic_id, models.User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Compte actif introuvable.")
    raw = create_reset_token(db, email=user.email)
    delivered = bool(raw and send_reset_email(user.email, raw))
    ClinicalAuditService.log(db, actor=current_user, patient_id=None, clinic_id=clinic_id,
        action="password_reset_link", resource_type="staff", resource_id=user.id,
        client_ip=client_ip(request), user_agent=request.headers.get("user-agent"),
        reason=body.reason, after={"delivery_status": "sent" if delivered else "failed"})
    return {"id": user.id, "email": user.email, "delivery_status": "sent" if delivered else "failed"}


@router.post("/accounts/bulk")
def bulk_account_action(body: AccountBulkRequest, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_owner)):
    if body.action not in ("deactivate", "reactivate", "delete"):
        raise HTTPException(status_code=422, detail="Action groupée invalide.")
    if not body.reason.strip():
        raise HTTPException(status_code=422, detail="Une raison est obligatoire.")
    targets = db.query(models.User).filter(models.User.id.in_(set(body.user_ids))).all()
    preview = []
    for user in targets:
        if user.id == current_user.id or user.role in ("platform_owner", "platform_admin"):
            preview.append({"id": user.id, "email": user.email, "eligible": False, "reason": "Compte plateforme protégé"})
        elif user.clinic_id is None:
            preview.append({"id": user.id, "email": user.email, "eligible": False, "reason": "Compte orphelin à examiner individuellement"})
        else:
            preview.append({"id": user.id, "email": user.email, "clinic_id": user.clinic_id, "eligible": True})
    if not body.execute:
        return {"execute": False, "action": body.action, "items": preview}
    results = []
    for item in preview:
        if not item["eligible"]:
            results.append(item); continue
        try:
            kwargs = dict(db=db, clinic_id=item["clinic_id"], user_id=item["id"], actor=current_user, reason=body.reason, ip=client_ip(request), user_agent=request.headers.get("user-agent"))
            if body.action == "deactivate": lifecycle_deactivate_staff(**kwargs)
            elif body.action == "reactivate": lifecycle_reactivate_staff(**kwargs)
            else: lifecycle_delete_unused_staff(**kwargs)
            results.append({**item, "completed": True})
        except StaffLifecycleError as exc:
            db.rollback(); results.append({**item, "completed": False, "reason": exc.message})
    return {"execute": True, "action": body.action, "items": results}


@router.post("/clinic-admins", response_model=schemas.UserResponse, status_code=201)
def create_clinic_administrator(
    body: ClinicAdminCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_owner),
):
    clinic = db.query(models.Clinic).filter(models.Clinic.id == body.clinic_id).first()
    if not clinic:
        raise HTTPException(status_code=404, detail="Clinic not found")
    try:
        validate_password(body.password)
        provisioned = create_clinic_admin_user(
            db,
            email=body.email,
            password=body.password,
            clinic_id=body.clinic_id,
            channel="admin_api",
            actor_user_id=current_user.id,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except UserProvisioningError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    user = provisioned.user
    return schemas.UserResponse(id=user.id, email=user.email, role=user.role, doctor_id=None)


@router.patch("/users/{user_id}/status")
def set_user_status(
    user_id: int,
    body: UserStatusUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_admin),
):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.role == "platform_owner":
        raise HTTPException(status_code=400, detail="Cannot disable the platform owner account")
    if user.id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot disable your own account")
    if user.clinic_id is None:
        raise HTTPException(status_code=409, detail="Utilisez la gestion dédiée du compte après son rattachement à une clinique.")
    if not (body.reason or "").strip():
        raise HTTPException(status_code=422, detail="Une raison est obligatoire.")
    try:
        if body.is_active:
            user = lifecycle_reactivate_staff(db, clinic_id=user.clinic_id, user_id=user.id, actor=current_user, reason=body.reason or "", ip=None)
        else:
            user = lifecycle_deactivate_staff(db, clinic_id=user.clinic_id, user_id=user.id, actor=current_user, reason=body.reason or "", ip=None)
    except StaffLifecycleError as exc:
        _lifecycle_error(exc)
    return {"id": user.id, "email": user.email, "is_active": user.is_active}


@router.get("/audit-logs")
def platform_audit_logs(
    clinic_id: Optional[int] = None, actor_id: Optional[int] = None,
    action: Optional[str] = None, resource_type: Optional[str] = None,
    date_from: Optional[datetime] = None, date_to: Optional[datetime] = None,
    limit: int = Query(200, ge=1, le=1000),
    db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin),
):
    q = db.query(models.ClinicalAuditLog)
    if clinic_id is not None: q = q.filter(models.ClinicalAuditLog.clinic_id == clinic_id)
    if actor_id is not None: q = q.filter(models.ClinicalAuditLog.actor_id == actor_id)
    if action: q = q.filter(models.ClinicalAuditLog.action == action)
    if resource_type: q = q.filter(models.ClinicalAuditLog.resource_type == resource_type)
    if date_from: q = q.filter(models.ClinicalAuditLog.timestamp >= date_from)
    if date_to: q = q.filter(models.ClinicalAuditLog.timestamp <= date_to)
    logs = q.order_by(models.ClinicalAuditLog.timestamp.desc()).limit(limit).all()
    actor_ids = {row.actor_id for row in logs}
    actors = {u.id: u.email for u in db.query(models.User).filter(models.User.id.in_(actor_ids)).all()} if actor_ids else {}
    clinic_ids = {row.clinic_id for row in logs if row.clinic_id}
    clinics = {c.id: c.name for c in db.query(models.Clinic).filter(models.Clinic.id.in_(clinic_ids)).all()} if clinic_ids else {}
    return [{
        "id": row.id, "timestamp": row.timestamp, "actor_id": row.actor_id,
        "actor_email": actors.get(row.actor_id), "actor_role": row.actor_role,
        "clinic_id": row.clinic_id, "clinic_name": clinics.get(row.clinic_id),
        "action": row.action, "resource_type": row.resource_type, "resource_id": row.resource_id,
        "patient_id": row.patient_id, "ip": row.ip, "user_agent": row.user_agent,
        "reason": row.reason, "before": json.loads(row.before_json) if row.before_json else None,
        "after": json.loads(row.after_json) if row.after_json else None,
    } for row in logs]


def _audit_export_rows(db: Session, clinic_id: Optional[int], date_from: Optional[datetime], date_to: Optional[datetime]):
    q = db.query(models.ClinicalAuditLog)
    if clinic_id is not None: q = q.filter(models.ClinicalAuditLog.clinic_id == clinic_id)
    if date_from: q = q.filter(models.ClinicalAuditLog.timestamp >= date_from)
    if date_to: q = q.filter(models.ClinicalAuditLog.timestamp <= date_to)
    return q.order_by(models.ClinicalAuditLog.timestamp.desc()).limit(10000).all()


@router.get("/audit-logs/export.csv")
def export_platform_audit_csv(clinic_id: Optional[int] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["date", "actor_id", "role", "clinic_id", "action", "resource", "resource_id", "reason", "ip", "user_agent", "before", "after"])
    for row in _audit_export_rows(db, clinic_id, date_from, date_to):
        writer.writerow([row.timestamp.isoformat(), row.actor_id, row.actor_role, row.clinic_id or "", row.action, row.resource_type, row.resource_id or "", row.reason or "", row.ip or "", row.user_agent or "", row.before_json or "", row.after_json or ""])
    return Response(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": "attachment; filename=journal-audit.csv"})


@router.get("/audit-logs/export.pdf")
def export_platform_audit_pdf(clinic_id: Optional[int] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    buffer = io.BytesIO(); pdf = canvas.Canvas(buffer, pagesize=landscape(A4)); width, height = landscape(A4)
    y = height - 36; pdf.setFont("Helvetica-Bold", 14); pdf.drawString(36, y, "Journal d'audit plateforme"); y -= 26
    pdf.setFont("Helvetica", 7)
    for row in _audit_export_rows(db, clinic_id, date_from, date_to):
        line = f"{row.timestamp:%d/%m/%Y %H:%M:%S} | acteur #{row.actor_id} ({row.actor_role}) | clinique {row.clinic_id or '-'} | {row.action} {row.resource_type} #{row.resource_id or '-'} | {row.reason or '-'}"
        pdf.drawString(36, y, line[:190]); y -= 12
        if y < 30: pdf.showPage(); pdf.setFont("Helvetica", 7); y = height - 30
    pdf.save(); buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=journal-audit.pdf"})


@router.patch("/clinics/{clinic_id}/configuration")
def update_clinic_configuration(clinic_id: int, body: PlatformClinicConfigurationUpdate, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinique introuvable.")
    before = {"name": clinic.name, "address": clinic.address, "city": clinic.city, "phone": clinic.phone, "email": clinic.email, **clinic_configuration(clinic)}
    data = body.model_dump(exclude_unset=True)
    config_keys = {"enabled_modules", "payment_methods", "receipt_template", "catalogue_version", "offline_workstations_enabled", "data_retention_days", "mfa_policy", "trusted_workstation_days"}
    config = clinic_configuration(clinic)
    for key in tuple(data):
        if key in config_keys: config[key] = data.pop(key)
    for key, value in data.items(): setattr(clinic, key, value)
    clinic.configuration_json = json.dumps(config, ensure_ascii=False)
    ClinicalAuditService.log(db, actor=current_user, patient_id=None, clinic_id=clinic.id, action="update", resource_type="clinic_configuration", resource_id=clinic.id, client_ip=client_ip(request), user_agent=request.headers.get("user-agent"), before=before, after={"name": clinic.name, "address": clinic.address, "city": clinic.city, "phone": clinic.phone, "email": clinic.email, **config}, commit=False)
    db.commit()
    return {"id": clinic.id, "configuration": config, "name": clinic.name, "address": clinic.address, "city": clinic.city, "phone": clinic.phone, "email": clinic.email}


@router.post("/clinics/{clinic_id}/state")
def change_clinic_state(clinic_id: int, body: PlatformClinicStateRequest, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_owner)):
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinique introuvable.")
    if body.confirmation.strip() != clinic.name:
        raise HTTPException(status_code=409, detail="La confirmation doit correspondre exactement au nom de la clinique.")
    if body.action == "archive":
        active_admissions = db.query(models.Admission).filter(
            models.Admission.clinic_id == clinic_id,
            models.Admission.status.in_(("pending", "admitted", "in_care", "transferred")),
        ).count()
        if active_admissions: raise HTTPException(status_code=409, detail="Impossible d’archiver une clinique avec des hospitalisations actives.")
    before = {"is_active": clinic.is_active, "suspended_at": clinic.suspended_at, "archived_at": clinic.archived_at, "reason": clinic.suspension_reason}
    now = datetime.utcnow()
    if body.action == "suspend": clinic.is_active = False; clinic.suspended_at = now; clinic.suspension_reason = body.reason
    elif body.action == "archive": clinic.is_active = False; clinic.archived_at = now; clinic.suspended_at = clinic.suspended_at or now; clinic.suspension_reason = body.reason
    else: clinic.is_active = True; clinic.suspended_at = None; clinic.archived_at = None; clinic.suspension_reason = None
    staff_ids = [r[0] for r in db.query(models.User.id).filter(models.User.clinic_id == clinic_id).all()]
    if body.action != "reactivate":
        for uid in staff_ids: revoke_all_user_refresh_tokens(db, user_id=uid, commit=False)
        db.query(models.User).filter(models.User.id.in_(staff_ids)).update({models.User.session_version: models.User.session_version + 1}, synchronize_session=False)
    after = {"is_active": clinic.is_active, "suspended_at": clinic.suspended_at, "archived_at": clinic.archived_at, "reason": clinic.suspension_reason}
    ClinicalAuditService.log(db, actor=current_user, patient_id=None, clinic_id=clinic.id, action=body.action, resource_type="clinic", resource_id=clinic.id, client_ip=client_ip(request), user_agent=request.headers.get("user-agent"), reason=body.reason, before=before, after=after, commit=False)
    db.commit(); return {"id": clinic.id, **after}


@router.get("/clinics/{clinic_id}/health")
def platform_clinic_health(clinic_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    if not db.query(models.Clinic.id).filter(models.Clinic.id == clinic_id).first(): raise HTTPException(status_code=404, detail="Clinique introuvable.")
    return clinic_health(db, clinic_id)


@router.get("/clinics/{clinic_id}/data-governance")
def platform_data_governance(clinic_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    if not db.query(models.Clinic.id).filter(models.Clinic.id == clinic_id).first(): raise HTTPException(status_code=404, detail="Clinique introuvable.")
    return data_inventory(db, clinic_id)


@router.post("/clinics/{clinic_id}/data-reset")
def reset_clinic_data(clinic_id: int, body: PlatformDataResetRequest, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_owner)):
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinique introuvable.")
    if body.confirmation.strip() != clinic.name or not body.acknowledge_irreversible:
        raise HTTPException(status_code=409, detail="Confirmez le nom exact de la clinique et le caractère irréversible.")
    latest_backup = db.query(ClinicNodeBackupRecord).filter(
        ClinicNodeBackupRecord.clinic_id == clinic_id,
        ClinicNodeBackupRecord.verified.is_(True),
        ClinicNodeBackupRecord.created_at >= datetime.utcnow() - timedelta(hours=26),
    ).first()
    if not latest_backup and not body.waive_backup:
        raise HTTPException(status_code=409, detail="Aucune sauvegarde vérifiée depuis moins de 26 heures. Vérifiez une sauvegarde ou acceptez explicitement d’y renoncer.")
    before = data_inventory(db, clinic_id)
    patient_ids = [row[0] for row in db.query(models.Patient.id).filter(models.Patient.clinic_id == clinic_id).all()]
    from services.demo_patient_cleanup import purge_patient
    deleted = {}
    try:
        for patient_id in patient_ids:
            for key, count in purge_patient(db, patient_id).items(): deleted[key] = deleted.get(key, 0) + count
        config = clinic_configuration(clinic); config["offline_data_epoch"] = int(config.get("offline_data_epoch", 1)) + 1
        clinic.configuration_json = json.dumps(config, ensure_ascii=False)
        ClinicalAuditService.log(db, actor=current_user, patient_id=None, clinic_id=clinic.id, action="full_data_reset", resource_type="data_governance", resource_id=clinic.id, client_ip=client_ip(request), user_agent=request.headers.get("user-agent"), reason=body.reason, before=before, after={"deleted": deleted, "offline_data_epoch": config["offline_data_epoch"]}, commit=False)
        db.commit()
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="La remise à zéro a échoué; aucune suppression n’a été validée.") from exc
    return {"clinic_id": clinic.id, "deleted": deleted, "verification": data_inventory(db, clinic_id), "offline_data_epoch": config["offline_data_epoch"]}


@router.get("/clinics/{clinic_id}/patients/export.csv")
def export_clinic_patients(clinic_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_platform_admin)):
    clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
    if not clinic: raise HTTPException(status_code=404, detail="Clinique introuvable.")
    output = io.StringIO(); writer = csv.writer(output)
    writer.writerow(["id", "numero_dossier", "nom", "prenom", "telephone", "date_naissance", "sexe", "archive"])
    for p in db.query(models.Patient).filter(models.Patient.clinic_id == clinic_id).order_by(models.Patient.id).all():
        writer.writerow([p.id, p.patient_number or "", p.last_name or "", p.first_name or "", p.phone or "", p.date_of_birth or "", p.gender or "", bool(p.is_archived)])
    return Response(content="\ufeff" + output.getvalue(), media_type="text/csv; charset=utf-8", headers={"Content-Disposition": f"attachment; filename=patients-clinique-{clinic_id}.csv"})


@router.post("/clinics/{clinic_id}/patients/merge")
def merge_duplicate_patients(clinic_id: int, body: PlatformPatientMergeRequest, request: Request, db: Session = Depends(get_db), current_user=Depends(get_current_platform_owner)):
    if body.source_patient_id == body.target_patient_id:
        raise HTTPException(status_code=422, detail="La source et la cible doivent être différentes.")
    patients = db.query(models.Patient).filter(models.Patient.clinic_id == clinic_id, models.Patient.id.in_((body.source_patient_id, body.target_patient_id))).all()
    if len(patients) != 2: raise HTTPException(status_code=404, detail="Patients introuvables dans cette clinique.")
    by_id = {p.id: p for p in patients}; source = by_id[body.source_patient_id]; target = by_id[body.target_patient_id]
    if body.confirmation.strip() != (target.patient_number or str(target.id)):
        raise HTTPException(status_code=409, detail="Confirmez le numéro de dossier cible exact.")
    dependent = {}
    from database import Base
    patient_models = []
    for mapper in Base.registry.mappers:
        model = mapper.class_
        if model is models.Patient or not hasattr(model, "patient_id"): continue
        try:
            count = db.query(model).filter(model.patient_id == source.id).count()
        except Exception:
            continue
        if count: dependent[getattr(model, "__tablename__", model.__name__)] = count
        patient_models.append(model)
    preview = {"source": {"id": source.id, "patient_number": source.patient_number, "name": f"{source.first_name} {source.last_name}"}, "target": {"id": target.id, "patient_number": target.patient_number, "name": f"{target.first_name} {target.last_name}"}, "dependent_records": dependent}
    if not body.execute: return {"execute": False, **preview}
    before = preview
    try:
        for model in patient_models:
            db.query(model).filter(model.patient_id == source.id).update({model.patient_id: target.id}, synchronize_session=False)
        for field in ("phone", "email", "address", "date_of_birth"):
            if not getattr(target, field, None) and getattr(source, field, None): setattr(target, field, getattr(source, field))
        source_user_id = source.user_id
        db.delete(source); db.flush()
        if source_user_id and not db.query(models.Patient.id).filter(models.Patient.user_id == source_user_id).first():
            source_user = db.query(models.User).filter(models.User.id == source_user_id, models.User.role == "patient").first()
            if source_user: source_user.is_active = False; source_user.session_version = int(source_user.session_version or 0) + 1
        ClinicalAuditService.log(db, actor=current_user, patient_id=target.id, clinic_id=clinic_id, action="merge_duplicate", resource_type="patient", resource_id=target.id, client_ip=client_ip(request), user_agent=request.headers.get("user-agent"), reason=body.reason, before=before, after={"target_patient_id": target.id, "source_deleted": source.id}, commit=False)
        db.commit()
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=409, detail="La fusion a été annulée car certaines données ne peuvent pas être combinées sans conflit.") from exc
    return {"execute": True, **preview, "verification": {"source_exists": False, "target_id": target.id}}
