"""Platform Owner API — full platform administration (owner role only)."""

from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy.orm import Session

import models
import schemas
from schemas.clinical import ClinicResponse
from database import get_db
from security import get_current_platform_owner, validate_password
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
    current_user=Depends(get_current_platform_owner),
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
