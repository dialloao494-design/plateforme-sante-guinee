from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from sqlalchemy.orm import Session
import schemas
from database import get_db
from security import get_current_platform_owner
from services.user_service import UserService
from schemas.user import AdminUserCreate, UserResponse
from services.user_provisioning import (
    EmailAlreadyRegisteredError,
    create_admin_user,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[schemas.UserResponse])
def list_users(
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_owner),
):
    """List all registered users (admin only)."""
    return UserService.list_users(db)


@router.post("/admins", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def provision_administrator(
    body: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_platform_owner),
):
    """
    Create a new administrator account.

    Requires an existing authenticated admin. Public registration cannot assign ``admin``.
    """
    try:
        provisioned = create_admin_user(
            db,
            email=body.email,
            password=body.password,
            channel="admin_api",
            actor_user_id=current_user.id,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    user = provisioned.user
    return UserResponse(id=user.id, email=user.email, role=user.role, doctor_id=None)
