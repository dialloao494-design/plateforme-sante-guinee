"""Platform Owner API — full platform administration (owner role only)."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import or_
from sqlalchemy.orm import Session

import models
import schemas
from schemas.clinical import ClinicResponse
from schemas.platform import (
    PlatformClinicDetail,
    PlatformClinicSummary,
    PlatformOwnerSummary,
    PlatformStaffMember,
    PlatformStaffPasswordReset,
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
    from fastapi import HTTPException
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
        # Partial success is still useful — return 207-like payload with 200 + failures list
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
    user.must_change_password = False
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
    user.is_active = body.is_active
    db.commit()
    return {"id": user.id, "email": user.email, "is_active": user.is_active}
