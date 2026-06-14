"""Clinical reporting REST API."""

from __future__ import annotations

from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from core.clinical_access import CLINIC_OPS_ROLES, assert_role, resolve_clinic_for_user
from database import get_db
from models.user import User
from schemas.clinical_reports import ClinicalPeriodSummaryResponse, RevenueSummaryResponse
from security import get_current_user
from services.clinical_reporting_service import ClinicalReportingService

router = APIRouter(prefix="/clinical/reports", tags=["Clinical Reporting"])

REPORT_ROLES = CLINIC_OPS_ROLES


@router.get("/summary", response_model=ClinicalPeriodSummaryResponse)
def clinical_summary(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, REPORT_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    if not start or not end:
        start, end = ClinicalReportingService.default_period()
    data = ClinicalReportingService.period_summary(db, clinic_id=clinic.id, start=start, end=end)
    data["revenue"] = RevenueSummaryResponse(**data["revenue"])
    return ClinicalPeriodSummaryResponse(**data)


@router.get("/revenue", response_model=RevenueSummaryResponse)
def revenue_report(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, REPORT_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    if not start or not end:
        start, end = ClinicalReportingService.default_period()
    return ClinicalReportingService.revenue_summary(db, clinic_id=clinic.id, start=start, end=end)


@router.get("/export.csv")
def export_csv(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    assert_role(current_user, REPORT_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    if not start or not end:
        start, end = ClinicalReportingService.default_period()
    csv_text = ClinicalReportingService.export_csv(db, clinic_id=clinic.id, start=start, end=end)
    filename = f"rapport-clinique-{start.isoformat()}-{end.isoformat()}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/export.pdf")
def export_pdf(
    start: Optional[date] = Query(None),
    end: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.pdf_service import clinical_report_pdf

    assert_role(current_user, REPORT_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    if not start or not end:
        start, end = ClinicalReportingService.default_period()
    summary = ClinicalReportingService.period_summary(db, clinic_id=clinic.id, start=start, end=end)
    pdf_bytes = clinical_report_pdf(summary)
    filename = f"rapport-clinique-{start.isoformat()}-{end.isoformat()}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
