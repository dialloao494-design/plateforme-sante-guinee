"""Patient discharge REST API."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

import models
from core.clinical_access import RECEPTION_ROLES, DOCTOR_ROLES, ADMIN_ROLES, resolve_clinic_for_user
from core.http_utils import client_ip
from database import get_db
from models.user import User
from schemas.discharge import (
    DischargeChecklistResponse,
    DischargeRequest,
    DischargeSummaryResponse,
    OpenVisitResponse,
)
from security import get_current_user
from services.discharge_service import DischargeService
from services.pdf_service import discharge_pdf

router = APIRouter(prefix="/clinical/discharge", tags=["Patient Discharge"])

DISCHARGE_ROLES = RECEPTION_ROLES + DOCTOR_ROLES + ADMIN_ROLES


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    from fastapi import HTTPException

    if user.role not in allowed:
        raise HTTPException(status_code=403, detail=f"Requires one of roles: {list(allowed)}")


def _summary_response(summary: models.DischargeSummary) -> DischargeSummaryResponse:
    patient_name = None
    if summary.patient:
        patient_name = f"{summary.patient.first_name} {summary.patient.last_name}".strip()
    return DischargeSummaryResponse(
        id=summary.id,
        clinic_id=summary.clinic_id,
        patient_id=summary.patient_id,
        visit_id=summary.visit_id,
        discharge_type=summary.discharge_type,
        status=summary.status,
        diagnoses=summary.diagnoses,
        procedures=summary.procedures,
        medications=summary.medications,
        clinical_summary=summary.clinical_summary,
        follow_up_instructions=summary.follow_up_instructions,
        invoice_validated=summary.invoice_validated,
        archived_to_emr=summary.archived_to_emr,
        discharged_at=summary.discharged_at,
        patient_name=patient_name,
    )


@router.get("/visits/open", response_model=List[OpenVisitResponse])
def list_open_visits(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, DISCHARGE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    visits = DischargeService.list_open_visits(db, clinic_id=clinic.id)
    out = []
    for v in visits:
        name = None
        if v.patient:
            name = f"{v.patient.first_name} {v.patient.last_name}".strip()
        out.append(
            OpenVisitResponse(
                id=v.id,
                patient_id=v.patient_id,
                patient_name=name,
                status=v.status,
                consultation_id=v.consultation_id,
                started_at=v.started_at,
            )
        )
    return out


@router.get("/checklist/{visit_id}", response_model=DischargeChecklistResponse)
def discharge_checklist(
    visit_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, DISCHARGE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    return DischargeService.get_checklist(db, clinic_id=clinic.id, visit_id=visit_id)


@router.post("/execute", response_model=DischargeSummaryResponse, status_code=201)
def execute_discharge(
    payload: DischargeRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, DISCHARGE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    summary = DischargeService.discharge_patient(
        db,
        clinic_id=clinic.id,
        visit_id=payload.visit_id,
        actor=current_user,
        follow_up_instructions=payload.follow_up_instructions,
        force=payload.force,
        client_ip=client_ip(request),
    )
    return _summary_response(summary)


@router.get("/summaries", response_model=List[DischargeSummaryResponse])
def list_summaries(
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, DISCHARGE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    summaries = DischargeService.list_summaries(db, clinic_id=clinic.id, patient_id=patient_id)
    return [_summary_response(s) for s in summaries]


@router.get("/summaries/{summary_id}/pdf")
def discharge_pdf_download(
    summary_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, DISCHARGE_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    summary = (
        db.query(models.DischargeSummary)
        .filter(models.DischargeSummary.id == summary_id, models.DischargeSummary.clinic_id == clinic.id)
        .first()
    )
    if not summary:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Discharge summary not found")
    patient_name = f"{summary.patient.first_name} {summary.patient.last_name}".strip() if summary.patient else "—"
    pdf_bytes = discharge_pdf(
        patient_name,
        {
            "discharge_type": summary.discharge_type,
            "diagnoses": summary.diagnoses,
            "procedures": summary.procedures,
            "medications": summary.medications,
            "clinical_summary": summary.clinical_summary,
            "follow_up_instructions": summary.follow_up_instructions,
        },
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="sortie-{summary_id}.pdf"'},
    )
