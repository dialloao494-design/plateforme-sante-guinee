"""Radiology / imaging REST API."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

import models
from core.clinical_access import DOCTOR_ROLES, ADMIN_ROLES, resolve_clinic_for_user, doctor_for_user
from core.http_utils import client_ip
from database import get_db
from models.user import User
from schemas.radiology import (
    ImagingOrderCreate,
    ImagingOrderResponse,
    ImagingOrderStatusUpdate,
    ImagingReportCreate,
    ImagingResultResponse,
)
from security import get_current_user
from services.imaging_service import ImagingService

router = APIRouter(prefix="/clinical/radiology", tags=["Radiology"])

RADIOLOGY_ROLES = ("doctor", "admin", "lab_technician")


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    from fastapi import HTTPException

    if user.role not in allowed:
        raise HTTPException(status_code=403, detail=f"Requires one of roles: {list(allowed)}")


def _order_response(order: models.ImagingOrder) -> ImagingOrderResponse:
    patient_name = None
    if order.patient:
        patient_name = f"{order.patient.first_name} {order.patient.last_name}".strip()
    results = [
        ImagingResultResponse(
            id=r.id,
            order_id=r.order_id,
            findings=r.findings,
            impression=r.impression,
            recommendations=r.recommendations,
            status=r.status,
            reported_at=r.reported_at,
            validated_at=r.validated_at,
        )
        for r in (order.results or [])
    ]
    return ImagingOrderResponse(
        id=order.id,
        clinic_id=order.clinic_id,
        patient_id=order.patient_id,
        consultation_id=order.consultation_id,
        modality=order.modality,
        body_part=order.body_part,
        clinical_indication=order.clinical_indication,
        priority=order.priority,
        status=order.status,
        scheduled_at=order.scheduled_at,
        patient_name=patient_name,
        results=results,
    )


@router.get("/orders", response_model=List[ImagingOrderResponse])
def list_orders(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, RADIOLOGY_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    orders = ImagingService.list_queue(db, clinic_id=clinic.id, status=status)
    return [_order_response(o) for o in orders]


@router.post("/consultations/{consultation_id}/orders", response_model=ImagingOrderResponse, status_code=201)
def create_order(
    consultation_id: int,
    payload: ImagingOrderCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, DOCTOR_ROLES + ADMIN_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    order = ImagingService.create_order(
        db,
        clinic_id=clinic.id,
        consultation_id=consultation_id,
        modality=payload.modality,
        body_part=payload.body_part,
        clinical_indication=payload.clinical_indication,
        priority=payload.priority,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return _order_response(order)


@router.patch("/orders/{order_id}", response_model=ImagingOrderResponse)
def update_order_status(
    order_id: int,
    payload: ImagingOrderStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, RADIOLOGY_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    order = ImagingService.update_status(
        db,
        clinic_id=clinic.id,
        order_id=order_id,
        status=payload.status,
        scheduled_at=payload.scheduled_at,
    )
    return _order_response(order)


@router.post("/orders/{order_id}/report", response_model=ImagingResultResponse, status_code=201)
def submit_report(
    order_id: int,
    payload: ImagingReportCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, RADIOLOGY_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    result = ImagingService.submit_report(
        db,
        clinic_id=clinic.id,
        order_id=order_id,
        findings=payload.findings,
        impression=payload.impression,
        recommendations=payload.recommendations,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return ImagingResultResponse(
        id=result.id,
        order_id=result.order_id,
        findings=result.findings,
        impression=result.impression,
        recommendations=result.recommendations,
        status=result.status,
        reported_at=result.reported_at,
        validated_at=result.validated_at,
    )


@router.post("/results/{result_id}/validate", response_model=ImagingResultResponse)
def validate_report(
    result_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, DOCTOR_ROLES + ADMIN_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    result = ImagingService.validate_report(
        db,
        clinic_id=clinic.id,
        result_id=result_id,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return ImagingResultResponse(
        id=result.id,
        order_id=result.order_id,
        findings=result.findings,
        impression=result.impression,
        recommendations=result.recommendations,
        status=result.status,
        reported_at=result.reported_at,
        validated_at=result.validated_at,
    )


@router.get("/results/{result_id}/pdf")
def imaging_report_pdf_download(
    result_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi import HTTPException
    from fastapi.responses import Response

    from services.pdf_service import imaging_report_pdf

    _require_role(current_user, RADIOLOGY_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    result = (
        db.query(models.ImagingResult)
        .join(models.ImagingOrder)
        .filter(
            models.ImagingResult.id == result_id,
            models.ImagingOrder.clinic_id == clinic.id,
            models.ImagingResult.status == "validated",
        )
        .first()
    )
    if not result:
        raise HTTPException(status_code=404, detail="Validated imaging result not found")
    order = result.order
    patient_name = "—"
    if order.patient:
        patient_name = f"{order.patient.first_name} {order.patient.last_name}".strip()
    pdf_bytes = imaging_report_pdf(
        patient_name,
        {
            "modality": order.modality,
            "body_part": order.body_part,
            "clinical_indication": order.clinical_indication,
        },
        {
            "findings": result.findings,
            "impression": result.impression,
            "recommendations": result.recommendations,
        },
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="imagerie-{result_id}.pdf"'},
    )
