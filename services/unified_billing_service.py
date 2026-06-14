"""Unified billing — aggregate charges into patient invoices."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from models.user import User
from services.cis_audit import log_cis
from services.clinic_billing_service import ClinicBillingService
from services.visit_service import VisitService

DEFAULT_RADIOLOGY_FEE_GNF = 150_000
DEFAULT_HOSPITALIZATION_DAILY_GNF = 200_000
DEFAULT_NURSING_FEE_GNF = 50_000
DEFAULT_OXYGEN_FEE_GNF = 35_000
DEFAULT_PROCEDURE_FEE_GNF = 100_000

CHARGE_TYPE_LABELS = {
    "consultation": "Consultation",
    "laboratory": "Laboratoire",
    "radiology": "Radiologie",
    "pharmacy": "Pharmacie",
    "hospitalization": "Hospitalisation",
    "nursing": "Soins infirmiers",
    "oxygen": "Oxygénothérapie",
    "procedure": "Acte médical",
}


class UnifiedBillingService:
    @staticmethod
    def _invoice_number(db: Session, clinic_id: int) -> str:
        count = db.query(models.Invoice).filter(models.Invoice.clinic_id == clinic_id).count()
        year = datetime.utcnow().year
        return f"INV-{year}-{clinic_id:03d}-{count + 1:05d}"

    @staticmethod
    def collect_pending_charges(
        db: Session, *, clinic_id: int, patient_id: int, visit_id: int | None = None
    ) -> list[models.ClinicCharge]:
        q = db.query(models.ClinicCharge).filter(
            models.ClinicCharge.clinic_id == clinic_id,
            models.ClinicCharge.patient_id == patient_id,
            models.ClinicCharge.payment_status == "pending",
            models.ClinicCharge.invoice_id.is_(None),
        )
        if visit_id:
            q = q.filter(
                (models.ClinicCharge.visit_id == visit_id) | (models.ClinicCharge.visit_id.is_(None))
            )
        return q.all()

    @staticmethod
    def add_hospitalization_charges(
        db: Session, *, visit: models.ClinicalVisit, admission: models.Admission | None
    ) -> None:
        if not admission:
            return
        days = 1
        if admission.admitted_at:
            delta = datetime.utcnow() - admission.admitted_at
            days = max(1, delta.days or 1)
        UnifiedBillingService._ensure_charge(
            db,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            visit_id=visit.id,
            charge_type="hospitalization",
            source_type="admission",
            source_id=admission.id,
            description=f"Hospitalisation ({days} jour(s))",
            amount_gnf=DEFAULT_HOSPITALIZATION_DAILY_GNF * days,
        )
        UnifiedBillingService._ensure_charge(
            db,
            clinic_id=visit.clinic_id,
            patient_id=visit.patient_id,
            visit_id=visit.id,
            charge_type="nursing",
            source_type="admission",
            source_id=admission.id,
            description="Soins infirmiers",
            amount_gnf=DEFAULT_NURSING_FEE_GNF,
        )

    @staticmethod
    def add_imaging_charges(db: Session, *, visit: models.ClinicalVisit, consultation_id: int) -> None:
        orders = (
            db.query(models.ImagingOrder)
            .filter(
                models.ImagingOrder.consultation_id == consultation_id,
                models.ImagingOrder.status.in_(["reported", "validated"]),
            )
            .all()
        )
        for order in orders:
            UnifiedBillingService._ensure_charge(
                db,
                clinic_id=visit.clinic_id,
                patient_id=visit.patient_id,
                visit_id=visit.id,
                charge_type="radiology",
                source_type="imaging_order",
                source_id=order.id,
                description=f"Imagerie {order.modality} — {order.body_part or 'examen'}",
                amount_gnf=DEFAULT_RADIOLOGY_FEE_GNF,
            )

    @staticmethod
    def _ensure_charge(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        visit_id: int,
        charge_type: str,
        source_type: str,
        source_id: int,
        description: str,
        amount_gnf: int,
    ) -> models.ClinicCharge:
        existing = ClinicBillingService._existing_charge(
            db, clinic_id=clinic_id, source_type=source_type, source_id=source_id
        )
        if existing:
            if not existing.visit_id:
                existing.visit_id = visit_id
                db.commit()
            return existing
        charge = models.ClinicCharge(
            clinic_id=clinic_id,
            patient_id=patient_id,
            visit_id=visit_id,
            charge_type=charge_type,
            source_type=source_type,
            source_id=source_id,
            description=description,
            amount_gnf=amount_gnf,
            payment_status="pending",
        )
        db.add(charge)
        db.commit()
        db.refresh(charge)
        return charge

    @staticmethod
    def generate_invoice(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        visit_id: int | None,
        actor: User,
        client_ip: str | None = None,
    ) -> models.Invoice:
        visit = None
        if visit_id:
            visit = (
                db.query(models.ClinicalVisit)
                .filter(models.ClinicalVisit.id == visit_id, models.ClinicalVisit.clinic_id == clinic_id)
                .first()
            )
        if not visit:
            visit = VisitService.get_or_create_for_patient_clinic(
                db, clinic_id=clinic_id, patient_id=patient_id
            )
            visit_id = visit.id

        admission = None
        if visit.admission_id:
            admission = db.query(models.Admission).filter(models.Admission.id == visit.admission_id).first()
        elif visit.consultation_id:
            admission = (
                db.query(models.Admission)
                .filter(
                    models.Admission.consultation_id == visit.consultation_id,
                    models.Admission.status.notin_(["cancelled"]),
                )
                .first()
            )
            if admission:
                visit.admission_id = admission.id

        UnifiedBillingService.add_hospitalization_charges(db, visit=visit, admission=admission)
        if visit.consultation_id:
            UnifiedBillingService.add_imaging_charges(
                db, visit=visit, consultation_id=visit.consultation_id
            )

        charges = UnifiedBillingService.collect_pending_charges(
            db, clinic_id=clinic_id, patient_id=patient_id, visit_id=visit.id
        )
        if not charges:
            raise HTTPException(status_code=400, detail="Aucune charge en attente pour cette visite")

        invoice = models.Invoice(
            clinic_id=clinic_id,
            patient_id=patient_id,
            visit_id=visit.id,
            invoice_number=UnifiedBillingService._invoice_number(db, clinic_id),
            status="issued",
            issued_at=datetime.utcnow(),
            created_by_user_id=actor.id,
        )
        db.add(invoice)
        db.flush()

        total = 0
        for charge in charges:
            item = models.InvoiceItem(
                invoice_id=invoice.id,
                charge_type=charge.charge_type,
                source_type=charge.source_type,
                source_id=charge.source_id,
                description=charge.description,
                quantity=1,
                unit_price_gnf=charge.amount_gnf,
                amount_gnf=charge.amount_gnf,
                clinic_charge_id=charge.id,
            )
            charge.invoice_id = invoice.id
            charge.visit_id = visit.id
            total += charge.amount_gnf
            db.add(item)

        invoice.total_amount_gnf = total
        visit.status = "billing"
        db.commit()
        db.refresh(invoice)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=patient_id,
            action="create",
            resource_type="invoice",
            resource_id=invoice.id,
            client_ip=client_ip,
        )
        return invoice

    @staticmethod
    def pay_invoice(
        db: Session,
        *,
        clinic_id: int,
        invoice_id: int,
        payment_method: str,
        actor: User,
        client_ip: str | None = None,
    ) -> models.Invoice:
        invoice = (
            db.query(models.Invoice)
            .filter(models.Invoice.id == invoice_id, models.Invoice.clinic_id == clinic_id)
            .first()
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Invoice not found")
        if invoice.status == "paid":
            raise HTTPException(status_code=400, detail="Invoice already paid")
        remaining = invoice.total_amount_gnf - invoice.paid_amount_gnf
        if remaining <= 0:
            raise HTTPException(status_code=400, detail="Nothing to pay")

        payment = models.PaymentRecord(
            invoice_id=invoice.id,
            amount_gnf=remaining,
            payment_method=payment_method,
            recorded_by_user_id=actor.id,
        )
        db.add(payment)
        invoice.paid_amount_gnf = invoice.total_amount_gnf
        invoice.status = "paid"
        invoice.paid_at = datetime.utcnow()

        for item in invoice.items:
            if item.clinic_charge_id:
                charge = db.query(models.ClinicCharge).filter(models.ClinicCharge.id == item.clinic_charge_id).first()
                if charge:
                    charge.payment_status = "paid"
                    charge.payment_method = payment_method
                    charge.paid_at = datetime.utcnow()
                    charge.recorded_by_user_id = actor.id

        if invoice.visit_id:
            visit = db.query(models.ClinicalVisit).filter(models.ClinicalVisit.id == invoice.visit_id).first()
            if visit:
                visit.status = "paid"

        db.commit()
        db.refresh(invoice)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=invoice.patient_id,
            action="pay",
            resource_type="invoice",
            resource_id=invoice.id,
            client_ip=client_ip,
        )
        return invoice

    @staticmethod
    def list_invoices(db: Session, *, clinic_id: int, status: str | None = None) -> list[models.Invoice]:
        q = db.query(models.Invoice).filter(models.Invoice.clinic_id == clinic_id)
        if status:
            q = q.filter(models.Invoice.status == status)
        return q.order_by(models.Invoice.created_at.desc()).all()
