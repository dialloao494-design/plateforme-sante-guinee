"""Laboratory Phase 2 endpoints — catalog, dashboard, register."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from core.clinical_access import resolve_clinic_for_user
from database import get_db
from models.user import User
from security import get_current_user
from services.lab_clinical_service import LabClinicalService

router = APIRouter(prefix="/clinical/lab", tags=["Laboratory Phase 2"])

LAB_READ = ("lab_technician", "doctor", "clinic_admin", "admin", "receptionist", "platform_admin", "platform_owner")


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    if user.role not in allowed:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires one of roles: {list(allowed)}")


@router.get("/catalog")
def lab_catalog(current_user: User = Depends(get_current_user)):
    _require_role(current_user, LAB_READ)
    return {"tests": LabClinicalService.test_catalog()}


@router.get("/dashboard")
def lab_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_role(current_user, LAB_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    return LabClinicalService.dashboard_stats(db, clinic_id=clinic.id)


@router.get("/reports/monthly")
def lab_monthly_report(
    year: Optional[int] = Query(None),
    month: Optional[int] = Query(None, ge=1, le=12),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, LAB_READ)
    from datetime import date

    today = date.today()
    clinic = resolve_clinic_for_user(db, current_user)
    return LabClinicalService.monthly_report(
        db, clinic_id=clinic.id, year=year or today.year, month=month or today.month
    )


@router.get("/results/validated")
def lab_validated_results(
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, LAB_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    rows = LabClinicalService.list_validated_results(db, clinic_id=clinic.id, limit=limit)
    out = []
    for res in rows:
        order = res.lab_order
        patient = order.patient if order else None
        out.append(
            {
                "id": res.id,
                "order_id": order.id if order else None,
                "test_name": order.test_name if order else None,
                "test_code": order.test_code if order else None,
                "patient_id": order.patient_id if order else None,
                "patient_name": f"{patient.first_name} {patient.last_name}" if patient else None,
                "result_summary": res.result_summary,
                "status": res.status,
                "validated_at": res.validated_at.isoformat() if res.validated_at else None,
            }
        )
    return out
