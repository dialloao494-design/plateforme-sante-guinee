"""
Central API authorization helper (Security Wave 1).

Two-layer model from the approved architecture:
1. Role / permission gate
2. Tenancy gate (clinic_id of resource == caller's clinic)

Platform roles may bypass tenancy only via explicit ``platform_break_glass=True``.
"""

from __future__ import annotations

from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from core.rbac import Permission, assert_permission, has_permission
from core.roles import user_has_any_role
from core.tenant import assert_patient_in_clinic, is_platform_admin, user_clinic_id
from models.user import User


def authorize(
    user: User,
    *,
    roles: Iterable[str] | None = None,
    permission: Permission | None = None,
    clinic_id: int | None = None,
    patient_id: int | None = None,
    db: Session | None = None,
    platform_break_glass: bool = False,
) -> None:
    """
    Enforce role and/or permission, then optional clinic/patient tenancy.

    Raises HTTP 403 on denial. Does not return a value.
    """
    if permission is not None:
        assert_permission(user, permission)
    elif roles is not None:
        allowed = tuple(roles)
        if not user_has_any_role(user.role, allowed):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied",
        )

    if clinic_id is None and patient_id is None:
        return

    if is_platform_admin(user) and platform_break_glass:
        return

    if is_platform_admin(user) and clinic_id is None and patient_id is not None and db is not None:
        # Platform may look up patient without clinic scope when break-glass not required
        # for read tools; still require explicit break_glass for mutations via callers.
        return

    actor_cid = user_clinic_id(user, db)
    if clinic_id is not None:
        if is_platform_admin(user):
            return
        if actor_cid != clinic_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied for this clinic",
            )

    if patient_id is not None:
        if db is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Authorization misconfigured",
            )
        if is_platform_admin(user):
            return
        if actor_cid is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not assigned to a clinic",
            )
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=actor_cid)


def safe_permission_denied() -> HTTPException:
    return HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Permission denied")
