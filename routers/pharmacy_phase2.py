"""Pharmacy Phase 2 endpoints — dashboard and monthly register."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.clinical_access import resolve_clinic_for_user
from database import get_db
from models.user import User
from security import get_current_user
from services.pharmacy_clinical_service import PharmacyClinicalService

router = APIRouter(prefix="/clinical/pharmacy", tags=["Pharmacy Phase 2"])

PHARMACY_READ = ("pharmacist", "doctor", "clinic_admin", "admin", "receptionist", "cashier", "platform_admin", "platform_owner")


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    if user.role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires one of roles: {list(allowed)}")


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
