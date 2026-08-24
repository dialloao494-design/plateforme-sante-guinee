"""Reception HIS REST API — central clinic entry point."""

from __future__ import annotations

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import Response
from sqlalchemy.orm import Session, joinedload

import models
from core.clinical_access import (
    BILLING_PAY_ROLES,
    BILLING_READ_ROLES,
    RECEPTION_ROLES,
    resolve_clinic_for_user,
)
from core.http_utils import client_ip
from database import get_db
from models.user import User
from schemas.reception_his import (
    DuplicateCheckRequest,
    DuplicatePatientMatch,
    PatientRegistrationCreate,
    PatientRegistrationUpdate,
    PatientRegistrationResponse,
    PatientSearchResult,
    ReceptionAdmissionCreate,
    ReceptionAdmissionResponse,
    ReceptionDashboardStats,
    ReceptionInvoiceCreate,
    ReceptionInvoiceResponse,
    ReceptionPaymentCreate,
    ReceptionPeriodReport,
    RefundCreate,
    RefundResponse,
    RefundStatusUpdate,
    PaymentRecordOut,
    InvoiceItemOut,
    ServiceRequestCreate,
    ServiceRequestUpdate,
    ServiceRequestResponse,
)
from security import get_current_user
from services.reception_his_service import ReceptionHisService

router = APIRouter(prefix="/clinical/reception/his", tags=["Reception HIS"])


def _require_reception(user: User) -> None:
    if user.role not in RECEPTION_ROLES and user.role not in (
        "admin",
        "clinic_admin",
        "platform_admin",
        "platform_owner",
    ):
        raise HTTPException(status_code=403, detail="Accès réservé à la réception")


def _require_billing_read(user: User) -> None:
    """Reception HIS invoice read — reception + cashier + clinic admins."""
    if user.role in BILLING_READ_ROLES or user.role in (
        "admin",
        "clinic_admin",
        "platform_admin",
        "platform_owner",
    ):
        return
    raise HTTPException(status_code=403, detail="Accès facturation requis")


def _require_billing_pay(user: User) -> None:
    """Reception HIS invoice payment — receptionist and cashier (BILLING_PAY_ROLES)."""
    if user.role in BILLING_PAY_ROLES or user.role in (
        "admin",
        "clinic_admin",
        "platform_admin",
        "platform_owner",
    ):
        return
    raise HTTPException(status_code=403, detail="Accès encaissement requis")


def _patient_out(patient: models.Patient) -> PatientSearchResult:
    return PatientSearchResult(
        id=patient.id,
        patient_number=patient.patient_number,
        qr_token=patient.qr_token,
        first_name=patient.first_name,
        last_name=patient.last_name,
        phone=patient.phone,
        age=patient.age or 0,
        age_value=getattr(patient, "age_value", None),
        age_unit=getattr(patient, "age_unit", None),
        gender=patient.gender,
        date_of_birth=patient.date_of_birth,
        date_of_birth_precision=getattr(patient, "date_of_birth_precision", None),
        payer_json=patient.payer_json,
        phone_secondary=patient.phone_secondary,
        email=patient.email,
        address=patient.address,
        commune=patient.commune,
        city=patient.city,
        region=patient.region,
        country=patient.country,
        place_of_birth=patient.place_of_birth,
        nationality=patient.nationality,
        marital_status=patient.marital_status,
        mother_first_name=patient.mother_first_name,
        mother_last_name=patient.mother_last_name,
        profession=patient.profession,
        preferred_language=patient.preferred_language,
        photo_url=patient.photo_url,
        emergency_contact_json=patient.emergency_contact_json,
        is_newborn=patient.is_newborn,
        registration_date=patient.registration_date,
        created_at=patient.created_at,
    )


def _service_request_out(row: models.ClinicServiceRequest) -> ServiceRequestResponse:
    data = ReceptionHisService._serialize_service_request(row)
    return ServiceRequestResponse(**data)


def _invoice_out(invoice: models.Invoice) -> ReceptionInvoiceResponse:
    patient_name = None
    patient_number = None
    if invoice.patient:
        patient_name = f"{invoice.patient.first_name} {invoice.patient.last_name}".strip()
        patient_number = invoice.patient.patient_number
    cashier_name = None
    if invoice.created_by_user:
        from services.pdf_service import printed_by_label

        cashier_name = printed_by_label(invoice.created_by_user)
    remaining = max(0, invoice.total_amount_gnf - invoice.paid_amount_gnf)
    description = invoice.items[0].description if invoice.items else None
    payments = [
        PaymentRecordOut(
            id=p.id,
            amount_gnf=p.amount_gnf,
            payment_method=p.payment_method,
            reference=p.reference,
            paid_at=p.paid_at,
        )
        for p in sorted(invoice.payments or [], key=lambda x: x.paid_at)
    ]
    status = invoice.status
    if status in ("issued", "partially_paid") and remaining <= 0 and invoice.paid_amount_gnf > 0:
        status = "paid"
    elif status == "issued" and invoice.paid_amount_gnf > 0:
        status = "partially_paid"
    elif status == "issued" and invoice.paid_amount_gnf == 0:
        status = "unpaid"
    items_out = [
        InvoiceItemOut(
            id=i.id,
            charge_type=i.charge_type,
            description=i.description,
            quantity=i.quantity,
            unit_price_gnf=i.unit_price_gnf,
            amount_gnf=i.amount_gnf,
        )
        for i in (invoice.items or [])
    ]
    subtotal = int(getattr(invoice, "subtotal_amount_gnf", None) or invoice.total_amount_gnf or 0)
    exemption_percent = float(getattr(invoice, "exemption_percent", None) or 0)
    exemption_amount = int(getattr(invoice, "exemption_amount_gnf", None) or 0)
    return ReceptionInvoiceResponse(
        id=invoice.id,
        invoice_number=invoice.invoice_number,
        patient_id=invoice.patient_id,
        patient_name=patient_name,
        patient_number=patient_number,
        cashier_name=cashier_name,
        department=invoice.department,
        status=status,
        subtotal_amount_gnf=subtotal,
        exemption_percent=exemption_percent,
        exemption_amount_gnf=exemption_amount,
        total_amount_gnf=invoice.total_amount_gnf,
        paid_amount_gnf=invoice.paid_amount_gnf,
        remaining_balance_gnf=remaining,
        issued_at=invoice.issued_at,
        description=description,
        items=items_out,
        payments=payments,
    )


def _refund_out(refund: models.ClinicRefund) -> RefundResponse:
    patient_name = None
    if refund.patient:
        patient_name = f"{refund.patient.first_name} {refund.patient.last_name}".strip()
    invoice_number = refund.invoice.invoice_number if refund.invoice else None
    return RefundResponse(
        id=refund.id,
        refund_number=refund.refund_number,
        patient_id=refund.patient_id,
        patient_name=patient_name,
        invoice_id=refund.invoice_id,
        invoice_number=invoice_number,
        original_amount_paid_gnf=refund.original_amount_paid_gnf,
        service_paid_for=refund.service_paid_for,
        amount_consumed_gnf=refund.amount_consumed_gnf,
        refund_amount_gnf=refund.refund_amount_gnf,
        reason=refund.reason,
        reason_notes=refund.reason_notes,
        recipient_name=refund.recipient_name,
        recipient_relationship=refund.recipient_relationship,
        recipient_phone=refund.recipient_phone,
        refund_method=refund.refund_method,
        status=refund.status,
        created_at=refund.created_at,
        approved_at=refund.approved_at,
        paid_at=refund.paid_at,
    )


@router.get("/billing-catalog")
def billing_catalog(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Consultation, imaging and lab tariffs for reception billing."""
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    from data.aasma_billing_catalog import (
        ADMISSION_SERVICES,
        CONSULTATION_SERVICES,
        IMAGING_EXAMINATIONS,
        BILLING_DEPARTMENTS,
        SERVICE_PRESTATIONS,
        SPECIALIZED_SPECIALTIES,
        SURGICAL_ACTS,
    )

    lab_tests = []
    try:
        from services.lab_clinical_service import LabClinicalService

        catalog = LabClinicalService.catalog_payload(db, clinic_id=clinic.id)
        for cat in catalog.get("categories") or []:
            for test in cat.get("tests") or []:
                lab_tests.append(
                    {
                        "code": test.get("code"),
                        "name": test.get("name"),
                        "category": cat.get("label"),
                        "price_gnf": test.get("price_gnf"),
                        "charge_type": "laboratory",
                    }
                )
    except Exception:
        lab_tests = []

    return {
        "admission_services": ADMISSION_SERVICES,
        "consultation_services": CONSULTATION_SERVICES,
        "specialized_specialties": SPECIALIZED_SPECIALTIES,
        "imaging_examinations": IMAGING_EXAMINATIONS,
        "service_prestations": SERVICE_PRESTATIONS,
        "surgical_acts": SURGICAL_ACTS,
        "billing_departments": BILLING_DEPARTMENTS,
        "lab_tests": lab_tests,
    }


@router.get("/dashboard", response_model=ReceptionDashboardStats)
def reception_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    return ReceptionHisService.dashboard_stats(db, clinic_id=clinic.id)


@router.get("/patients/search", response_model=List[PatientSearchResult])
def search_patients(
    q: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    patients = ReceptionHisService.search_patients(db, clinic_id=clinic.id, query=q)
    return [_patient_out(p) for p in patients]


@router.get("/patients/{patient_id}", response_model=PatientSearchResult)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
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
    return _patient_out(patient)


@router.get("/dashboard/queue")
def dashboard_queue(
    bucket: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    return ReceptionHisService.dashboard_queue(db, clinic_id=clinic.id, bucket=bucket)


@router.get("/service-requests", response_model=List[ServiceRequestResponse])
def list_service_requests(
    patient_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    rows = ReceptionHisService.list_service_requests(
        db, clinic_id=clinic.id, patient_id=patient_id, q=q, status=status
    )
    return [_service_request_out(r) for r in rows]


@router.get("/service-requests/lookup", response_model=ServiceRequestResponse)
def lookup_service_request(
    q: str = Query(..., min_length=1, description="N° demande (DSR-…) ou id numérique"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Resolve a registered service request for billing (paste ID into facturation)."""
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    row = ReceptionHisService.get_service_request_by_number(
        db, clinic_id=clinic.id, request_number=q
    )
    return _service_request_out(row)


@router.post("/service-requests", response_model=ServiceRequestResponse, status_code=201)
def create_service_request(
    body: ServiceRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    row = ReceptionHisService.create_service_request(
        db, clinic_id=clinic.id, payload=body, actor=current_user
    )
    row = (
        db.query(models.ClinicServiceRequest)
        .options(joinedload(models.ClinicServiceRequest.patient))
        .filter(models.ClinicServiceRequest.id == row.id)
        .first()
    )
    return _service_request_out(row)


@router.patch("/service-requests/{request_id}", response_model=ServiceRequestResponse)
def update_service_request(
    request_id: int,
    body: ServiceRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    row = ReceptionHisService.update_service_request(
        db, clinic_id=clinic.id, request_id=request_id, payload=body, actor=current_user
    )
    return _service_request_out(row)


@router.delete("/service-requests/{request_id}", status_code=204)
def delete_service_request(
    request_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    ReceptionHisService.delete_service_request(db, clinic_id=clinic.id, request_id=request_id)
    return Response(status_code=204)


@router.post("/patients/check-duplicates", response_model=List[DuplicatePatientMatch])
def check_duplicates(
    body: DuplicateCheckRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    return ReceptionHisService.find_duplicates(db, clinic_id=clinic.id, payload=body)


@router.post("/patients", response_model=PatientRegistrationResponse, status_code=201)
def register_patient(
    body: PatientRegistrationCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    patient = ReceptionHisService.register_patient(
        db,
        clinic_id=clinic.id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    return PatientRegistrationResponse.model_validate(patient)


@router.put("/patients/{patient_id}", response_model=PatientRegistrationResponse)
def update_patient(
    patient_id: int,
    body: PatientRegistrationUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    patient = ReceptionHisService.update_patient(
        db, clinic_id=clinic.id, patient_id=patient_id, payload=body,
        actor=current_user, client_ip=client_ip(request),
    )
    return PatientRegistrationResponse.model_validate(patient)


@router.post("/admissions", response_model=ReceptionAdmissionResponse, status_code=201)
def create_admission(
    body: ReceptionAdmissionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    admission = ReceptionHisService.create_admission(
        db,
        clinic_id=clinic.id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    patient = db.query(models.Patient).filter(models.Patient.id == admission.patient_id).first()
    patient_name = f"{patient.first_name} {patient.last_name}".strip() if patient else None
    import json

    services = []
    if admission.services_json:
        try:
            services = json.loads(admission.services_json)
        except (TypeError, json.JSONDecodeError):
            services = []
    if not services and admission.department:
        services = [s.strip() for s in admission.department.split(",") if s.strip()]
    return ReceptionAdmissionResponse(
        id=admission.id,
        admission_number=admission.admission_number,
        patient_id=admission.patient_id,
        patient_name=patient_name,
        department=admission.department,
        services=services,
        admission_type=admission.admission_type,
        status=admission.status,
        admitted_at=admission.admitted_at,
        attending_clinician_user_id=admission.attending_clinician_user_id,
    )


@router.post("/invoices", response_model=ReceptionInvoiceResponse, status_code=201)
def create_invoice(
    body: ReceptionInvoiceCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    invoice = ReceptionHisService.create_invoice(
        db,
        clinic_id=clinic.id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    invoice = ReceptionHisService.get_invoice(db, clinic_id=clinic.id, invoice_id=invoice.id)
    return _invoice_out(invoice)


@router.get("/invoices", response_model=List[ReceptionInvoiceResponse])
def list_invoices(
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_billing_read(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    if not patient_id:
        return []
    invoices = ReceptionHisService.list_invoices(db, clinic_id=clinic.id, patient_id=patient_id)
    return [_invoice_out(i) for i in invoices]


@router.get("/invoices/{invoice_id}", response_model=ReceptionInvoiceResponse)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_billing_read(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    invoice = ReceptionHisService.get_invoice(db, clinic_id=clinic.id, invoice_id=invoice_id)
    if not invoice:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Facture introuvable")
    return _invoice_out(invoice)


@router.post("/invoices/{invoice_id}/payments", response_model=ReceptionInvoiceResponse)
def add_payment(
    invoice_id: int,
    body: ReceptionPaymentCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_billing_pay(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    invoice = ReceptionHisService.add_payment(
        db,
        clinic_id=clinic.id,
        invoice_id=invoice_id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    invoice = ReceptionHisService.get_invoice(db, clinic_id=clinic.id, invoice_id=invoice.id)
    return _invoice_out(invoice)


@router.get("/invoices/search", response_model=ReceptionInvoiceResponse)
def search_invoice(
    q: str = Query(..., min_length=1),
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_billing_read(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    invoice = ReceptionHisService.find_invoice(
        db, clinic_id=clinic.id, query=q, patient_id=patient_id
    )
    if not invoice:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Facture introuvable")
    return _invoice_out(invoice)


@router.get("/reports", response_model=ReceptionPeriodReport)
def reception_period_report(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    return ReceptionHisService.period_report(db, clinic_id=clinic.id, start=start, end=end)


@router.get("/reports/export.csv")
def reception_report_csv(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    report = ReceptionHisService.period_report(db, clinic_id=clinic.id, start=start, end=end)
    csv_text = ReceptionHisService.export_report_csv(report)
    return Response(
        content=csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="rapport-reception-{start}.csv"'},
    )


@router.get("/reports/export.pdf")
def reception_report_pdf(
    start: date = Query(...),
    end: date = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    report = ReceptionHisService.period_report(db, clinic_id=clinic.id, start=start, end=end)
    from services.pdf_service import build_simple_pdf

    lines = [
        f"Période: {report['period_start']} → {report['period_end']}",
        f"Patients enregistrés: {report['patients_registered']}",
        f"Admissions: {report['admissions']}",
        f"Hospitalisations: {report['hospitalizations']}",
        f"Factures payées: {report['invoices_paid']}",
        f"Factures impayées: {report['invoices_unpaid']}",
        f"Paiements reçus: {report['payments_received_gnf']:,} GNF".replace(",", " "),
        f"Remboursements: {report['refunds_gnf']:,} GNF".replace(",", " "),
        f"Recettes nettes: {report['net_revenue_gnf']:,} GNF".replace(",", " "),
        "",
        "Recettes par service:",
    ]
    for svc, amt in (report.get("revenue_by_service") or {}).items():
        lines.append(f"  {svc}: {amt:,} GNF".replace(",", " "))
    pdf_bytes = build_simple_pdf("RAPPORT RÉCEPTION — CLINIQUE AASMA", lines)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="rapport-reception-{start}.pdf"'},
    )


@router.get("/invoices/{invoice_id}/receipt")
def print_receipt(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_billing_read(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    invoice = ReceptionHisService.get_invoice(db, clinic_id=clinic.id, invoice_id=invoice_id)
    if not invoice:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Facture introuvable")
    from datetime import datetime

    from services.pdf_service import invoice_pdf as build_invoice_pdf, printed_by_label

    patient_name = (
        f"{invoice.patient.first_name} {invoice.patient.last_name}".strip() if invoice.patient else "—"
    )
    patient_file = ""
    if invoice.patient:
        patient_file = invoice.patient.patient_number or str(invoice.patient.id)
    items = [
        {
            "description": i.description,
            "quantity": i.quantity,
            "unit_price_gnf": i.unit_price_gnf,
            "amount_gnf": i.amount_gnf,
        }
        for i in (invoice.items or [])
    ]
    methods = list({p.payment_method for p in (invoice.payments or []) if p.payment_method})
    method_labels = {
        "cash": "Espèces",
        "orange_money": "Orange Money",
        "bank_transfer": "Virement bancaire",
        "card": "Carte bancaire",
        "insurance": "Assurance",
    }
    payment_details = [
        {
            "method": p.payment_method,
            "label": method_labels.get(p.payment_method, p.payment_method),
            "amount_gnf": p.amount_gnf,
        }
        for p in (invoice.payments or [])
    ]
    subtotal = int(getattr(invoice, "subtotal_amount_gnf", None) or invoice.total_amount_gnf or 0)
    now = datetime.now()
    pdf_bytes = build_invoice_pdf(
        invoice.invoice_number,
        patient_name,
        items,
        subtotal=subtotal,
        exemption_percent=float(getattr(invoice, "exemption_percent", None) or 0),
        exemption_amount=int(getattr(invoice, "exemption_amount_gnf", None) or 0),
        total=invoice.total_amount_gnf,
        paid=invoice.paid_amount_gnf,
        payment_methods=methods,
        payment_details=payment_details,
        printed_by=printed_by_label(current_user),
        printed_date=now.strftime("%d/%m/%Y"),
        printed_time=now.strftime("%H:%M"),
        patient_file_number=patient_file,
    )
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="recu-{invoice.invoice_number}.pdf"'},
    )


@router.post("/refunds", response_model=RefundResponse, status_code=201)
def create_refund(
    body: RefundCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    refund = ReceptionHisService.create_refund(
        db,
        clinic_id=clinic.id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    refund = (
        db.query(models.ClinicRefund)
        .options(joinedload(models.ClinicRefund.patient), joinedload(models.ClinicRefund.invoice))
        .filter(models.ClinicRefund.id == refund.id)
        .first()
    )
    return _refund_out(refund)


@router.get("/refunds", response_model=List[RefundResponse])
def list_refunds(
    patient_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    refunds = ReceptionHisService.list_refunds(db, clinic_id=clinic.id, patient_id=patient_id)
    return [_refund_out(r) for r in refunds]


@router.patch("/refunds/{refund_id}", response_model=RefundResponse)
def update_refund(
    refund_id: int,
    body: RefundStatusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    refund = ReceptionHisService.update_refund_status(
        db,
        clinic_id=clinic.id,
        refund_id=refund_id,
        payload=body,
        actor=current_user,
        client_ip=client_ip(request),
    )
    refund = (
        db.query(models.ClinicRefund)
        .options(joinedload(models.ClinicRefund.patient), joinedload(models.ClinicRefund.invoice))
        .filter(models.ClinicRefund.id == refund.id)
        .first()
    )
    return _refund_out(refund)


@router.get("/refunds/{refund_id}/receipt")
def print_refund_receipt(
    refund_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_reception(current_user)
    clinic = resolve_clinic_for_user(db, current_user)
    refund = (
        db.query(models.ClinicRefund)
        .options(joinedload(models.ClinicRefund.patient), joinedload(models.ClinicRefund.invoice))
        .filter(models.ClinicRefund.id == refund_id, models.ClinicRefund.clinic_id == clinic.id)
        .first()
    )
    if not refund:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Remboursement introuvable")
    from services.pdf_service import printed_by_label, refund_receipt_pdf

    pdf_bytes = refund_receipt_pdf(refund, clinic_name=clinic.name, printed_by=printed_by_label(current_user))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="remboursement-{refund.refund_number}.pdf"'},
    )
