"""Pharmacy Phase 2 endpoints — dashboard, service requests, patient lookup."""

from __future__ import annotations

from typing import List, Optional

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

import models
from core.clinical_access import resolve_clinic_for_user
from core.roles import user_has_any_role
from database import get_db
from models.user import User
from schemas.clinical import DoctorMedicineDeliveryCreate, DoctorMedicineDeliveryResponse
from schemas.pharmacy_his import (
    PharmacyChargePaymentCreate,
    PharmacyChargePaymentLegacyCreate,
    PharmacyPatientOut,
    PharmacyRefundCreate,
    PharmacyRefundEligibleCharge,
    PharmacyRefundOut,
    PharmacyServiceRequestCreate,
    PharmacyServiceRequestResponse,
    PharmacyStockOrderCreate,
    PharmacyStockOrderOut,
)
from security import get_current_user
from services.doctor_medicine_delivery_service import DoctorMedicineDeliveryService
from services.cis_audit import log_cis
from services.pharmacy_clinical_service import PharmacyClinicalService
from services.pharmacy_inventory_service import PharmacyInventoryService
from services.reception_his_service import ReceptionHisService

router = APIRouter(prefix="/clinical/pharmacy", tags=["Pharmacy Phase 2"])

PHARMACY_READ = ("pharmacist", "doctor", "clinic_admin", "admin", "receptionist", "cashier", "platform_admin", "platform_owner")
PHARMACY_WRITE = ("pharmacist", "clinic_admin", "admin", "doctor")
PHARMACY_STOCK_WRITE = ("pharmacist", "clinic_admin", "admin")
PHARMACY_REFUND_WRITE = ("pharmacist", "clinic_admin", "admin")


def _stock_order_out(row: models.PharmacyStockOrder) -> PharmacyStockOrderOut:
    return PharmacyStockOrderOut(
        id=row.id,
        order_number=f"CMD-{int(row.clinic_id):03d}-{int(row.id):06d}",
        inventory_item_id=row.inventory_item_id,
        medication_name=row.medication_name,
        quantity=row.quantity,
        supplier=row.supplier,
        status=row.status,
        ordered_at=row.ordered_at,
        received_at=row.received_at,
    )


def _require_role(user: User, allowed: tuple[str, ...]) -> None:
    if not user_has_any_role(user.role, allowed):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Requires one of roles: {list(allowed)}")


def _pharmacy_patient_out(patient: models.Patient) -> PharmacyPatientOut:
    return PharmacyPatientOut(
        id=patient.id,
        patient_number=patient.patient_number,
        qr_token=patient.qr_token,
        first_name=patient.first_name,
        last_name=patient.last_name,
        date_of_birth=patient.date_of_birth,
        age=patient.age or 0,
        gender=patient.gender,
        profession=patient.profession,
        address=patient.address,
        city=patient.city,
        region=patient.region,
        country=patient.country,
        phone=patient.phone,
        quartier=patient.quartier,
    )


@router.get("/patients/search", response_model=List[PharmacyPatientOut])
def search_pharmacy_patients(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    patients = ReceptionHisService.search_patients(db, clinic_id=clinic.id, query=q)
    return [_pharmacy_patient_out(p) for p in patients]


@router.get("/patients/{patient_id}", response_model=PharmacyPatientOut)
def get_pharmacy_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    patient = (
        db.query(models.Patient)
        .filter(
            models.Patient.id == patient_id,
            models.Patient.clinic_id == clinic.id,
            models.Patient.is_archived.is_(False),
        )
        .first()
    )
    if not patient:
        raise HTTPException(status_code=404, detail="Patient introuvable")
    return _pharmacy_patient_out(patient)


@router.post("/service-requests", response_model=PharmacyServiceRequestResponse, status_code=201)
def create_pharmacy_service_request(
    body: PharmacyServiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.create_service_request(
        db, clinic_id=clinic.id, payload=body, actor=current_user
    )


@router.post("/charges/{charge_id}/pay", response_model=PharmacyServiceRequestResponse)
def pay_pharmacy_service_charge(
    charge_id: int,
    body: PharmacyChargePaymentLegacyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.pay_service_charge(
        db,
        clinic_id=clinic.id,
        charge_id=charge_id,
        payload=body,
        actor=current_user,
    )


@router.post("/charges/{charge_id}/payments", response_model=PharmacyServiceRequestResponse)
def add_pharmacy_charge_payment(
    charge_id: int,
    body: PharmacyChargePaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.add_charge_payment(
        db,
        clinic_id=clinic.id,
        charge_id=charge_id,
        payload=body,
        actor=current_user,
    )


@router.get("/charges/{charge_id}/receipt")
def pharmacy_charge_receipt(
    charge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.pdf_service import invoice_pdf, printed_by_label

    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    charge = (
        db.query(models.ClinicCharge)
        .options(joinedload(models.ClinicCharge.payments), joinedload(models.ClinicCharge.patient))
        .filter(
            models.ClinicCharge.id == charge_id,
            models.ClinicCharge.clinic_id == clinic.id,
            models.ClinicCharge.charge_type == "pharmacy",
        )
        .first()
    )
    if not charge:
        raise HTTPException(status_code=404, detail="Facture pharmacie introuvable")
    order = (
        db.query(models.PharmacyOrder)
        .filter(
            models.PharmacyOrder.clinic_id == clinic.id,
            models.PharmacyOrder.id == charge.source_id,
        )
        .first()
    )
    lines = PharmacyClinicalService._line_items_from_order(order) if order else []
    items = [
        {
            "description": l.get("product_name", "—"),
            "quantity": l.get("quantity", 1),
            "unit_price_gnf": l.get("unit_price_gnf", 0),
            "amount_gnf": l.get("total_gnf", 0),
        }
        for l in lines
    ]
    method_labels = {
        "cash": "Espèces",
        "orange_money": "Orange Money",
        "bank_transfer": "Virement",
        "card": "Carte bancaire",
        "insurance": "Assurance",
    }
    payment_details = [
        {
            "method": p.payment_method,
            "label": method_labels.get(p.payment_method, p.payment_method),
            "amount_gnf": p.amount_gnf,
        }
        for p in (charge.payments or [])
    ]
    patient_name = "—"
    patient_file = ""
    if charge.patient:
        patient_name = f"{charge.patient.last_name} {charge.patient.first_name}".strip()
        patient_file = charge.patient.patient_number or str(charge.patient.id)
    now = datetime.utcnow()
    pdf_bytes = invoice_pdf(
        f"PHARM-{charge.id}",
        patient_name,
        items,
        subtotal=int(charge.subtotal_amount_gnf or charge.amount_gnf),
        exemption_percent=float(charge.exemption_percent or 0),
        exemption_amount=int(charge.exemption_amount_gnf or 0),
        total=int(charge.amount_gnf),
        paid=int(charge.paid_amount_gnf or 0),
        payment_details=payment_details,
        printed_by=printed_by_label(current_user),
        printed_date=now.strftime("%d/%m/%Y"),
        printed_time=now.strftime("%H:%M"),
        patient_file_number=patient_file,
        document_title="REÇU PHARMACIE",
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recu-pharmacie-{charge.id}.pdf"'},
    )


@router.get("/dashboard")
def pharmacy_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.dashboard_stats(db, clinic_id=clinic.id)


@router.get("/refunds/eligible", response_model=List[PharmacyRefundEligibleCharge])
def eligible_pharmacy_refunds(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.eligible_refund_charges(db, clinic_id=clinic.id)


@router.get("/refunds", response_model=List[PharmacyRefundOut])
def list_pharmacy_refunds(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    return PharmacyClinicalService.list_refunds(db, clinic_id=clinic.id)


@router.post("/refunds", response_model=PharmacyRefundOut, status_code=201)
def create_pharmacy_refund(
    body: PharmacyRefundCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_REFUND_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    result = PharmacyClinicalService.create_refund(
        db, clinic_id=clinic.id, payload=body, actor=current_user
    )
    log_cis(
        db,
        actor=current_user,
        clinic_id=clinic.id,
        action="create",
        resource_type="pharmacy_refund",
        resource_id=result["id"],
        patient_id=result["patient_id"],
        after={
            "refund_number": result["refund_number"],
            "charge_id": result["charge_id"],
            "amount_gnf": result["amount_gnf"],
            "reason": result["reason"],
        },
        reason=body.reason_notes,
    )
    return result


@router.get("/refunds/{refund_id}/receipt")
def pharmacy_refund_receipt(
    refund_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from services.pdf_service import printed_by_label
    from services.refund_receipt_pdf_builder import build_refund_receipt_pdf

    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    row = (
        db.query(models.PharmacyRefund)
        .options(joinedload(models.PharmacyRefund.patient))
        .filter(models.PharmacyRefund.id == refund_id, models.PharmacyRefund.clinic_id == clinic.id)
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="Remboursement pharmacie introuvable")
    now = datetime.utcnow()
    items = PharmacyClinicalService._refund_items(row)
    patient_name = f"{row.patient.last_name} {row.patient.first_name}" if row.patient else "—"
    total_refunded = sum(
        int(value or 0)
        for (value,) in db.query(models.PharmacyRefund.amount_gnf).filter(
            models.PharmacyRefund.clinic_id == clinic.id,
            models.PharmacyRefund.charge_id == row.charge_id,
            models.PharmacyRefund.status == "paid",
        )
    )
    pdf_bytes = build_refund_receipt_pdf(
        clinic_name=clinic.name,
        refund_number=row.refund_number,
        invoice_number=f"PHARM-{row.charge_id}",
        patient_name=patient_name,
        patient_number=row.patient.patient_number if row.patient else "",
        service_paid_for=", ".join(f"{item['product_name']} × {item['quantity']}" for item in items),
        amount_consumed_gnf=max(0, int(row.charge.paid_amount_gnf or 0) - total_refunded),
        refund_amount_gnf=row.amount_gnf,
        reason=row.reason,
        reason_notes=row.reason_notes,
        recipient_name=row.recipient_name,
        recipient_phone=row.recipient_phone,
        refund_method=row.refund_method,
        status=row.status,
        printed_by=printed_by_label(current_user),
        printed_date=now.strftime("%d/%m/%Y"),
        printed_time=now.strftime("%H:%M"),
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="remboursement-{row.refund_number}.pdf"'},
    )


@router.get("/stock-orders", response_model=List[PharmacyStockOrderOut])
def list_pharmacy_stock_orders(
    db: Session = Depends(get_db), current_user: User = Depends(get_current_user)
):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    return [_stock_order_out(row) for row in PharmacyInventoryService.list_stock_orders(db, clinic_id=clinic.id)]


@router.post("/stock-orders", response_model=PharmacyStockOrderOut, status_code=201)
def create_pharmacy_stock_order(
    body: PharmacyStockOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_STOCK_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    row = PharmacyInventoryService.create_stock_order(
        db,
        clinic_id=clinic.id,
        inventory_item_id=body.inventory_item_id,
        medication_name=body.medication_name,
        quantity=body.quantity,
        supplier=body.supplier,
        actor_id=current_user.id,
    )
    log_cis(
        db,
        actor=current_user,
        clinic_id=clinic.id,
        action="create",
        resource_type="pharmacy_stock_order",
        resource_id=row.id,
        after={"status": row.status, "medication_name": row.medication_name, "quantity": row.quantity, "supplier": row.supplier},
    )
    return _stock_order_out(row)


@router.post("/stock-orders/{order_id}/{action}", response_model=PharmacyStockOrderOut)
def close_pharmacy_stock_order(
    order_id: int,
    action: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_STOCK_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    status_value = {"receive": "received", "cancel": "cancelled"}.get(action)
    if not status_value:
        raise HTTPException(status_code=404, detail="Action de commande inconnue")
    row = PharmacyInventoryService.update_stock_order_status(
        db,
        clinic_id=clinic.id,
        order_id=order_id,
        status=status_value,
        actor_id=current_user.id,
    )
    log_cis(
        db,
        actor=current_user,
        clinic_id=clinic.id,
        action="update",
        resource_type="pharmacy_stock_order",
        resource_id=row.id,
        before={"status": "ordered"},
        after={"status": row.status, "received_at": row.received_at.isoformat() if row.received_at else None},
    )
    return _stock_order_out(row)


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


@router.get("/doctor-deliveries", response_model=List[DoctorMedicineDeliveryResponse])
def list_doctor_deliveries(
    limit: int = Query(200, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_READ)
    clinic = resolve_clinic_for_user(db, current_user)
    rows = DoctorMedicineDeliveryService.list_deliveries(db, clinic_id=clinic.id, limit=limit)
    return rows


@router.post("/doctor-deliveries", response_model=DoctorMedicineDeliveryResponse, status_code=201)
def create_doctor_delivery(
    body: DoctorMedicineDeliveryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_role(current_user, PHARMACY_WRITE)
    clinic = resolve_clinic_for_user(db, current_user)
    return DoctorMedicineDeliveryService.create_delivery(
        db, clinic_id=clinic.id, payload=body, actor=current_user
    )
