"""Unified billing REST API."""

from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session

import models
from core.clinical_access import BILLING_PAY_ROLES, BILLING_READ_ROLES, resolve_clinic_for_user
from core.http_utils import client_ip
from database import get_db
from models.user import User
from schemas.billing_unified import InvoiceGenerateRequest, InvoicePayRequest, InvoiceResponse, InvoiceItemResponse
from security import get_current_user
from services.pdf_service import invoice_pdf_legacy
from services.unified_billing_service import UnifiedBillingService

router = APIRouter(prefix="/clinical/billing/unified", tags=["Unified Billing"])


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    from fastapi import HTTPException, status

    if user.role not in allowed:
        raise HTTPException(status_code=403, detail=f"Requires one of roles: {list(allowed)}")


def _invoice_response(invoice: models.Invoice) -> InvoiceResponse:
    patient_name = None
    if invoice.patient:
        patient_name = f"{invoice.patient.first_name} {invoice.patient.last_name}".strip()
    items = [
        InvoiceItemResponse(
            id=i.id,
            charge_type=i.charge_type,
            description=i.description,
            quantity=i.quantity,
            unit_price_gnf=i.unit_price_gnf,
            amount_gnf=i.amount_gnf,
        )
        for i in (invoice.items or [])
    ]
    return InvoiceResponse(
        id=invoice.id,
        clinic_id=invoice.clinic_id,
        patient_id=invoice.patient_id,
        visit_id=invoice.visit_id,
        invoice_number=invoice.invoice_number,
        status=invoice.status,
        total_amount_gnf=invoice.total_amount_gnf,
        paid_amount_gnf=invoice.paid_amount_gnf,
        issued_at=invoice.issued_at,
        paid_at=invoice.paid_at,
        patient_name=patient_name,
        items=items,
    )


@router.get("/invoices", response_model=List[InvoiceResponse])
def list_invoices(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, BILLING_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    invoices = UnifiedBillingService.list_invoices(db, clinic_id=clinic.id, status=status)
    return [_invoice_response(i) for i in invoices]


@router.post("/invoices/generate", response_model=InvoiceResponse, status_code=201)
def generate_invoice(
    payload: InvoiceGenerateRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, BILLING_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    invoice = UnifiedBillingService.generate_invoice(
        db,
        clinic_id=clinic.id,
        patient_id=payload.patient_id,
        visit_id=payload.visit_id,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return _invoice_response(invoice)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, BILLING_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.clinic_id == clinic.id)
        .first()
    )
    if not invoice:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Invoice not found")
    return _invoice_response(invoice)


@router.post("/invoices/{invoice_id}/pay", response_model=InvoiceResponse)
def pay_invoice(
    invoice_id: int,
    payload: InvoicePayRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, BILLING_PAY_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    invoice = UnifiedBillingService.pay_invoice(
        db,
        clinic_id=clinic.id,
        invoice_id=invoice_id,
        payment_method=payload.payment_method,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return _invoice_response(invoice)


@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf_download(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, BILLING_READ_ROLES)
    clinic = resolve_clinic_for_user(db, current_user)
    invoice = (
        db.query(models.Invoice)
        .filter(models.Invoice.id == invoice_id, models.Invoice.clinic_id == clinic.id)
        .first()
    )
    if not invoice:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Invoice not found")
    patient_name = f"{invoice.patient.first_name} {invoice.patient.last_name}".strip() if invoice.patient else "—"
    items = [{"description": i.description, "amount_gnf": i.amount_gnf} for i in invoice.items]
    pdf_bytes = invoice_pdf_legacy(invoice.invoice_number, patient_name, items, invoice.total_amount_gnf, invoice.paid_amount_gnf)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'},
    )
