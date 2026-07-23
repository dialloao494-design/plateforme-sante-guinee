"""Reception HIS — registration, admission, billing, refunds, dashboard."""

from __future__ import annotations

import json
import uuid
from datetime import date, datetime, time
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

import models
from models.user import User
from schemas.reception_his import (
    DuplicateCheckRequest,
    DuplicatePatientMatch,
    PatientRegistrationCreate,
    ReceptionAdmissionCreate,
    ReceptionInvoiceCreate,
    ReceptionPaymentCreate,
    RefundCreate,
    RefundStatusUpdate,
    ServiceRequestCreate,
    ServiceRequestUpdate,
)
from services.cis_audit import log_cis
from services.medical_history_service import ensure_medical_record


def _calc_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _normalize_phone(phone: str | None) -> str:
    if not phone:
        return ""
    return "".join(c for c in phone if c.isdigit())[-9:]


def _patient_number(clinic_id: int, patient_id: int) -> str:
    return f"PAT-{clinic_id:03d}-{patient_id:06d}"


def _qr_token(clinic_id: int) -> str:
    return f"AASMA-{clinic_id}-{uuid.uuid4().hex[:12].upper()}"


def _next_serial(db: Session, model, number_col, clinic_id: int, kind: str) -> str:
    """Allocate the next ADM/INV/RFD serial without colliding after deletions."""
    year = datetime.utcnow().year
    prefix = f"{kind}-{year}-{clinic_id:03d}-"
    rows = (
        db.query(number_col)
        .filter(
            model.clinic_id == clinic_id,
            number_col.like(f"{prefix}%"),
        )
        .all()
    )
    max_n = 0
    for (num,) in rows:
        if not num:
            continue
        try:
            max_n = max(max_n, int(str(num).rsplit("-", 1)[-1]))
        except ValueError:
            continue
    return f"{prefix}{max_n + 1:05d}"


def _admission_number(db: Session, clinic_id: int) -> str:
    return _next_serial(db, models.Admission, models.Admission.admission_number, clinic_id, "ADM")


def _invoice_number(db: Session, clinic_id: int) -> str:
    return _next_serial(db, models.Invoice, models.Invoice.invoice_number, clinic_id, "INV")


def _refund_number(db: Session, clinic_id: int) -> str:
    return _next_serial(db, models.ClinicRefund, models.ClinicRefund.refund_number, clinic_id, "RFD")


def _invoice_status(invoice: models.Invoice) -> str:
    remaining = invoice.total_amount_gnf - invoice.paid_amount_gnf
    if remaining <= 0 and invoice.paid_amount_gnf > 0:
        return "paid"
    if invoice.paid_amount_gnf > 0:
        return "partially_paid"
    return "unpaid" if invoice.status != "cancelled" else invoice.status


class ReceptionHisService:
    @staticmethod
    def find_duplicates(
        db: Session, *, clinic_id: int, payload: DuplicateCheckRequest
    ) -> list[DuplicatePatientMatch]:
        matches: dict[int, DuplicatePatientMatch] = {}
        base_q = db.query(models.Patient).filter(
            models.Patient.clinic_id == clinic_id,
            models.Patient.is_archived.is_(False),
        )

        if payload.phone:
            digits = _normalize_phone(payload.phone)
            if digits:
                for p in base_q.filter(models.Patient.phone.isnot(None)).all():
                    if _normalize_phone(p.phone) == digits:
                        entry = matches.get(p.id) or DuplicatePatientMatch(
                            id=p.id,
                            patient_number=p.patient_number,
                            first_name=p.first_name,
                            last_name=p.last_name,
                            phone=p.phone,
                            date_of_birth=p.date_of_birth,
                            match_reasons=[],
                        )
                        if "phone" not in entry.match_reasons:
                            entry.match_reasons.append("phone")
                        matches[p.id] = entry

        if payload.first_name and payload.last_name and payload.date_of_birth:
            fn = payload.first_name.strip().lower()
            ln = payload.last_name.strip().lower()
            for p in base_q.filter(models.Patient.date_of_birth == payload.date_of_birth).all():
                if p.first_name.strip().lower() == fn and p.last_name.strip().lower() == ln:
                    entry = matches.get(p.id) or DuplicatePatientMatch(
                        id=p.id,
                        patient_number=p.patient_number,
                        first_name=p.first_name,
                        last_name=p.last_name,
                        phone=p.phone,
                        date_of_birth=p.date_of_birth,
                        match_reasons=[],
                    )
                    if "name_dob" not in entry.match_reasons:
                        entry.match_reasons.append("name_dob")
                    matches[p.id] = entry

        return list(matches.values())

    @staticmethod
    def register_patient(
        db: Session,
        *,
        clinic_id: int,
        payload: PatientRegistrationCreate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.Patient:
        dupes = ReceptionHisService.find_duplicates(
            db,
            clinic_id=clinic_id,
            payload=DuplicateCheckRequest(
                phone=payload.phone,
                first_name=payload.first_name,
                last_name=payload.last_name,
                date_of_birth=payload.date_of_birth,
            ),
        )
        if dupes and not payload.confirm_duplicate:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "duplicate_patient",
                    "message": "Un ou plusieurs patients similaires existent déjà",
                    "matches": [m.model_dump(mode="json") for m in dupes],
                },
            )

        if payload.date_of_birth:
            age = _calc_age(payload.date_of_birth)
        elif payload.age_years is not None:
            age = payload.age_years
        else:
            raise HTTPException(
                status_code=422,
                detail="Indiquez une date de naissance ou saisissez l'âge du patient.",
            )
        emergency_json = payload.emergency_contact.model_dump()
        if payload.emergency_contact.same_address_as_patient:
            emergency_json["address"] = payload.address
            emergency_json["commune"] = payload.commune
            emergency_json["region"] = payload.region
            emergency_json["country"] = payload.country

        payer = payload.payer
        if payer.payer_type == "insurance" and not payer.insurance_company:
            raise HTTPException(status_code=400, detail="Assurance : nom de la compagnie requis")
        if payer.payer_type == "company" and not payer.company_name:
            raise HTTPException(status_code=400, detail="Entreprise : nom requis")

        mother_full = " ".join(
            x for x in (payload.mother_first_name or "", payload.mother_last_name or "") if x
        ).strip() or None

        patient = models.Patient(
            clinic_id=clinic_id,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            age=age,
            gender=payload.gender,
            date_of_birth=payload.date_of_birth,
            date_of_birth_precision=payload.date_of_birth_precision,
            phone=payload.phone.strip(),
            phone_secondary=(payload.phone_secondary or "").strip() or None,
            email=(payload.email or "").strip() or None,
            address=payload.address.strip(),
            commune=(payload.commune or "").strip() or None,
            city=(payload.city or "").strip() or None,
            region=(payload.region or "").strip() or None,
            country=(payload.country or "").strip() or None,
            place_of_birth=(payload.place_of_birth or "").strip() or None,
            nationality=(payload.nationality or "").strip() or None,
            marital_status=(payload.marital_status or "").strip() or None,
            preferred_language=(payload.preferred_language or "").strip() or None,
            photo_url=(payload.photo_url or "").strip() or None,
            mother_first_name=(payload.mother_first_name or "").strip() or None,
            mother_last_name=(payload.mother_last_name or "").strip() or None,
            mother_name=mother_full,
            profession=(payload.profession or "").strip() or None,
            emergency_contact=payload.emergency_contact.full_name,
            emergency_contact_json=json.dumps(emergency_json, ensure_ascii=False),
            payer_json=json.dumps(payer.model_dump(), ensure_ascii=False),
            qr_token=_qr_token(clinic_id),
            is_newborn=bool(payload.is_newborn),
            registration_date=payload.registration_date,
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        patient.patient_number = _patient_number(clinic_id, patient.id)
        db.commit()
        db.refresh(patient)

        ensure_medical_record(db, patient.id)
        if actor:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=patient.id,
                action="create",
                resource_type="patient",
                resource_id=patient.id,
                client_ip=client_ip,
            )
        return patient

    @staticmethod
    def search_patients(
        db: Session, *, clinic_id: int, query: str, limit: int = 25
    ) -> list[models.Patient]:
        q = query.strip()
        if not q:
            return []
        base = db.query(models.Patient).filter(
            models.Patient.clinic_id == clinic_id,
            models.Patient.is_archived.is_(False),
        )
        if q.isdigit():
            pid = int(q)
            by_id = base.filter(models.Patient.id == pid).first()
            if by_id:
                return [by_id]
            by_num = base.filter(models.Patient.patient_number.ilike(f"%{q}%")).limit(limit).all()
            if by_num:
                return by_num
        upper = q.upper()
        by_qr = base.filter(models.Patient.qr_token == upper).first()
        if by_qr:
            return [by_qr]
        pattern = f"%{q}%"
        if " " in q:
            parts = [p for p in q.split() if p.strip()]
            if len(parts) >= 2:
                first_pat = f"%{parts[0]}%"
                last_pat = f"%{parts[-1]}%"
                combo = (
                    base.filter(
                        models.Patient.first_name.ilike(first_pat),
                        models.Patient.last_name.ilike(last_pat),
                    )
                    .order_by(models.Patient.last_name, models.Patient.first_name)
                    .limit(limit)
                    .all()
                )
                if combo:
                    return combo
        return (
            base.filter(
                models.Patient.first_name.ilike(pattern)
                | models.Patient.last_name.ilike(pattern)
                | models.Patient.phone.ilike(pattern)
                | models.Patient.patient_number.ilike(pattern)
                | models.Patient.qr_token.ilike(pattern)
            )
            .order_by(models.Patient.last_name, models.Patient.first_name)
            .limit(limit)
            .all()
        )

    @staticmethod
    def create_admission(
        db: Session,
        *,
        clinic_id: int,
        payload: ReceptionAdmissionCreate,
        actor: User,
        client_ip: str | None = None,
    ) -> models.Admission:
        from core.tenant import assert_patient_in_clinic

        assert_patient_in_clinic(db, patient_id=payload.patient_id, clinic_id=clinic_id)

        if payload.admission_type == "hospitalization":
            existing = (
                db.query(models.Admission)
                .filter(
                    models.Admission.patient_id == payload.patient_id,
                    models.Admission.clinic_id == clinic_id,
                    models.Admission.admission_type == "hospitalization",
                    models.Admission.status.notin_(["discharged", "cancelled"]),
                )
                .first()
            )
            if existing:
                raise HTTPException(status_code=409, detail="Hospitalisation active déjà en cours")

        adm_time = payload.admission_time or datetime.utcnow().time()
        admitted_at = datetime.combine(payload.admission_date, adm_time)

        notes_parts = []
        if payload.confirmation_status:
            label = "Confirmée" if payload.confirmation_status == "confirmed" else "En attente"
            notes_parts.append(f"Confirmation: {label}")
        if payload.attending_physician_name and not payload.attending_clinician_user_id:
            notes_parts.append(f"Médecin: {payload.attending_physician_name.strip()}")
        if payload.notes:
            notes_parts.append(payload.notes.strip())
        combined_notes = "\n".join(notes_parts) if notes_parts else None

        status = "admitted" if payload.admission_type == "hospitalization" else "pending"
        if payload.admission_type == "emergency":
            status = "in_care"
        if payload.admission_type == "specialized_consultation":
            status = "pending"

        services = [s.strip() for s in (payload.services or []) if s and str(s).strip()]
        if not services and payload.department:
            services = [payload.department.strip()]
        department_label = ", ".join(services)

        specialty_code = (payload.specialty_code or "").strip() or None
        specialty_other = (payload.specialty_other or "").strip() or None
        specialty_label = None
        if specialty_code:
            from data.aasma_billing_catalog import SPECIALIZED_SPECIALTIES

            if specialty_code == "__other__":
                specialty_label = specialty_other
            else:
                specialty_label = next(
                    (s["label"] for s in SPECIALIZED_SPECIALTIES if s["code"] == specialty_code),
                    specialty_code,
                )

        admission = models.Admission(
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            admission_number=_admission_number(db, clinic_id),
            department=department_label,
            services_json=json.dumps(services, ensure_ascii=False),
            admission_type=payload.admission_type,
            status=status,
            attending_clinician_user_id=payload.attending_clinician_user_id,
            notes=combined_notes,
            specialty_code=specialty_code,
            specialty_other=specialty_other,
            admitted_by_user_id=actor.id,
            admitted_at=admitted_at,
        )
        db.add(admission)
        db.commit()
        db.refresh(admission)
        if specialty_label:
            record = ensure_medical_record(db, payload.patient_id)
            record.last_specialty = specialty_label
            db.commit()
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            action="create",
            resource_type="admission",
            resource_id=admission.id,
            client_ip=client_ip,
        )
        return admission

    @staticmethod
    def create_invoice(
        db: Session,
        *,
        clinic_id: int,
        payload: ReceptionInvoiceCreate,
        actor: User,
        client_ip: str | None = None,
    ) -> models.Invoice:
        from core.tenant import assert_patient_in_clinic
        from datetime import time

        assert_patient_in_clinic(db, patient_id=payload.patient_id, clinic_id=clinic_id)
        issued_at = datetime.utcnow()
        if payload.billing_date:
            issued_at = datetime.combine(payload.billing_date, time.min)

        line_payloads = []
        if payload.items:
            for row in payload.items:
                amt = int(row.quantity) * int(row.unit_price_gnf)
                line_payloads.append(
                    {
                        "charge_type": row.charge_type,
                        "description": row.description.strip(),
                        "quantity": int(row.quantity),
                        "unit_price_gnf": int(row.unit_price_gnf),
                        "amount_gnf": amt,
                        "source_type": row.source_type or "reception",
                    }
                )
        else:
            total = int(payload.total_amount_gnf or 0)
            line_payloads.append(
                {
                    "charge_type": "procedure",
                    "description": (payload.description or "").strip(),
                    "quantity": 1,
                    "unit_price_gnf": total,
                    "amount_gnf": total,
                    "source_type": "reception",
                }
            )

        subtotal = sum(int(l["amount_gnf"]) for l in line_payloads)
        exemption_percent = float(payload.exemption_percent or 0)
        exemption_amount = int(subtotal * exemption_percent / 100)
        net_total = max(0, subtotal - exemption_amount)

        invoice = models.Invoice(
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            invoice_number=_invoice_number(db, clinic_id),
            department=payload.department.strip(),
            status="issued",
            subtotal_amount_gnf=subtotal,
            exemption_percent=int(round(exemption_percent)),
            exemption_amount_gnf=exemption_amount,
            total_amount_gnf=net_total,
            paid_amount_gnf=0,
            issued_at=issued_at,
            created_by_user_id=actor.id,
        )
        db.add(invoice)
        db.flush()
        for idx, line in enumerate(line_payloads):
            item = models.InvoiceItem(
                invoice_id=invoice.id,
                charge_type=line["charge_type"],
                source_type=line["source_type"],
                source_id=invoice.id * 1000 + idx,
                description=line["description"],
                quantity=line["quantity"],
                unit_price_gnf=line["unit_price_gnf"],
                amount_gnf=line["amount_gnf"],
            )
            db.add(item)
        db.commit()
        db.refresh(invoice)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            action="create",
            resource_type="invoice",
            resource_id=invoice.id,
            client_ip=client_ip,
        )
        return invoice

    @staticmethod
    def add_payment(
        db: Session,
        *,
        clinic_id: int,
        invoice_id: int,
        payload: ReceptionPaymentCreate,
        actor: User,
        client_ip: str | None = None,
    ) -> models.Invoice:
        invoice = (
            db.query(models.Invoice)
            .options(joinedload(models.Invoice.payments))
            .filter(models.Invoice.id == invoice_id, models.Invoice.clinic_id == clinic_id)
            .first()
        )
        if not invoice:
            raise HTTPException(status_code=404, detail="Facture introuvable")
        if invoice.status == "cancelled":
            raise HTTPException(status_code=400, detail="Facture annulée")

        remaining = invoice.total_amount_gnf - invoice.paid_amount_gnf
        if remaining <= 0:
            raise HTTPException(status_code=400, detail="Facture déjà soldée")
        if payload.amount_gnf > remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Montant supérieur au reste à payer ({remaining} GNF)",
            )

        payment = models.PaymentRecord(
            invoice_id=invoice.id,
            amount_gnf=payload.amount_gnf,
            payment_method=payload.payment_method,
            reference=payload.reference,
            recorded_by_user_id=actor.id,
        )
        db.add(payment)
        invoice.paid_amount_gnf += payload.amount_gnf
        remaining_after = invoice.total_amount_gnf - invoice.paid_amount_gnf
        if remaining_after <= 0:
            invoice.status = "paid"
            invoice.paid_at = datetime.utcnow()
        else:
            invoice.status = "partially_paid"
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
    def get_invoice(
        db: Session, *, clinic_id: int, invoice_id: int
    ) -> models.Invoice | None:
        return (
            db.query(models.Invoice)
            .options(
                joinedload(models.Invoice.payments),
                joinedload(models.Invoice.patient),
                joinedload(models.Invoice.items),
            )
            .filter(models.Invoice.id == invoice_id, models.Invoice.clinic_id == clinic_id)
            .first()
        )

    @staticmethod
    def list_invoices(
        db: Session, *, clinic_id: int, patient_id: int | None = None
    ) -> list[models.Invoice]:
        q = (
            db.query(models.Invoice)
            .options(joinedload(models.Invoice.payments), joinedload(models.Invoice.patient), joinedload(models.Invoice.items))
            .filter(models.Invoice.clinic_id == clinic_id)
        )
        if patient_id:
            q = q.filter(models.Invoice.patient_id == patient_id)
        return q.order_by(models.Invoice.created_at.desc()).limit(100).all()

    @staticmethod
    def create_refund(
        db: Session,
        *,
        clinic_id: int,
        payload: RefundCreate,
        actor: User,
        client_ip: str | None = None,
    ) -> models.ClinicRefund:
        invoice = ReceptionHisService.get_invoice(db, clinic_id=clinic_id, invoice_id=payload.invoice_id)
        if not invoice:
            raise HTTPException(status_code=404, detail="Facture introuvable")
        if payload.refund_amount_gnf > invoice.paid_amount_gnf:
            raise HTTPException(status_code=400, detail="Remboursement supérieur au montant payé")

        refund = models.ClinicRefund(
            clinic_id=clinic_id,
            patient_id=invoice.patient_id,
            invoice_id=invoice.id,
            refund_number=_refund_number(db, clinic_id),
            original_amount_paid_gnf=invoice.paid_amount_gnf,
            service_paid_for=payload.service_paid_for.strip(),
            amount_consumed_gnf=payload.amount_consumed_gnf,
            refund_amount_gnf=payload.refund_amount_gnf,
            reason=payload.reason,
            reason_notes=payload.reason_notes,
            recipient_name=payload.recipient_name.strip(),
            recipient_relationship=payload.recipient_relationship,
            recipient_phone=payload.recipient_phone.strip(),
            refund_method=payload.refund_method,
            status="pending",
            created_by_user_id=actor.id,
        )
        db.add(refund)
        db.commit()
        db.refresh(refund)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=invoice.patient_id,
            action="create",
            resource_type="refund",
            resource_id=refund.id,
            client_ip=client_ip,
        )
        return refund

    @staticmethod
    def update_refund_status(
        db: Session,
        *,
        clinic_id: int,
        refund_id: int,
        payload: RefundStatusUpdate,
        actor: User,
        client_ip: str | None = None,
    ) -> models.ClinicRefund:
        refund = (
            db.query(models.ClinicRefund)
            .filter(models.ClinicRefund.id == refund_id, models.ClinicRefund.clinic_id == clinic_id)
            .first()
        )
        if not refund:
            raise HTTPException(status_code=404, detail="Remboursement introuvable")

        if payload.status == "approved":
            if refund.status != "pending":
                raise HTTPException(status_code=400, detail="Seuls les remboursements en attente peuvent être approuvés")
            refund.status = "approved"
            refund.approved_by_user_id = actor.id
            refund.approved_at = datetime.utcnow()
            if payload.refund_method:
                refund.refund_method = payload.refund_method
        elif payload.status == "rejected":
            if refund.status not in ("pending", "approved"):
                raise HTTPException(status_code=400, detail="Remboursement non rejetable")
            refund.status = "rejected"
        elif payload.status == "paid":
            if refund.status not in ("pending", "approved"):
                raise HTTPException(status_code=400, detail="Remboursement non payable")
            invoice = ReceptionHisService.get_invoice(db, clinic_id=clinic_id, invoice_id=refund.invoice_id)
            if not invoice:
                raise HTTPException(status_code=404, detail="Facture liée introuvable")
            refund.status = "paid"
            refund.paid_by_user_id = actor.id
            refund.paid_at = datetime.utcnow()
            if payload.refund_method:
                refund.refund_method = payload.refund_method
            # Reduce paid amount on invoice without deleting payment history
            new_paid = max(0, invoice.paid_amount_gnf - refund.refund_amount_gnf)
            invoice.paid_amount_gnf = new_paid
            remaining = invoice.total_amount_gnf - new_paid
            if remaining <= 0 and new_paid > 0:
                invoice.status = "paid"
            elif new_paid > 0:
                invoice.status = "partially_paid"
            else:
                invoice.status = "issued"

        db.commit()
        db.refresh(refund)
        log_cis(
            db,
            actor=actor,
            clinic_id=clinic_id,
            patient_id=refund.patient_id,
            action="update",
            resource_type="refund",
            resource_id=refund.id,
            client_ip=client_ip,
        )
        return refund

    @staticmethod
    def list_refunds(
        db: Session, *, clinic_id: int, patient_id: int | None = None
    ) -> list[models.ClinicRefund]:
        q = (
            db.query(models.ClinicRefund)
            .options(joinedload(models.ClinicRefund.patient), joinedload(models.ClinicRefund.invoice))
            .filter(models.ClinicRefund.clinic_id == clinic_id)
        )
        if patient_id:
            q = q.filter(models.ClinicRefund.patient_id == patient_id)
        return q.order_by(models.ClinicRefund.created_at.desc()).limit(100).all()

    @staticmethod
    def dashboard_stats(db: Session, *, clinic_id: int) -> dict[str, Any]:
        today = date.today()
        month_start = today.replace(day=1)
        start_today = datetime.combine(today, time.min)
        end_today = datetime.combine(today, time.max)
        start_month = datetime.combine(month_start, time.min)

        total_patients = (
            db.query(func.count(models.Patient.id))
            .filter(models.Patient.clinic_id == clinic_id, models.Patient.is_archived.is_(False))
            .scalar()
            or 0
        )
        patients_today = (
            db.query(func.count(models.Patient.id))
            .filter(
                models.Patient.clinic_id == clinic_id,
                models.Patient.is_archived.is_(False),
                models.Patient.created_at >= start_today,
                models.Patient.created_at <= end_today,
            )
            .scalar()
            or 0
        )
        admissions_today = (
            db.query(func.count(models.Admission.id))
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.admitted_at >= start_today,
                models.Admission.admitted_at <= end_today,
            )
            .scalar()
            or 0
        )
        hospitalized = (
            db.query(func.count(models.Admission.id))
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.admission_type == "hospitalization",
                models.Admission.status.in_(["admitted", "in_care", "pending"]),
            )
            .scalar()
            or 0
        )

        revenue_today = (
            db.query(func.coalesce(func.sum(models.PaymentRecord.amount_gnf), 0))
            .join(models.Invoice, models.PaymentRecord.invoice_id == models.Invoice.id)
            .filter(
                models.Invoice.clinic_id == clinic_id,
                models.PaymentRecord.paid_at >= start_today,
                models.PaymentRecord.paid_at <= end_today,
            )
            .scalar()
            or 0
        )
        refunds_today = (
            db.query(func.coalesce(func.sum(models.ClinicRefund.refund_amount_gnf), 0))
            .filter(
                models.ClinicRefund.clinic_id == clinic_id,
                models.ClinicRefund.status == "paid",
                models.ClinicRefund.paid_at >= start_today,
                models.ClinicRefund.paid_at <= end_today,
            )
            .scalar()
            or 0
        )
        revenue_today = int(revenue_today) - int(refunds_today)

        revenue_month = (
            db.query(func.coalesce(func.sum(models.PaymentRecord.amount_gnf), 0))
            .join(models.Invoice, models.PaymentRecord.invoice_id == models.Invoice.id)
            .filter(
                models.Invoice.clinic_id == clinic_id,
                models.PaymentRecord.paid_at >= start_month,
            )
            .scalar()
            or 0
        )
        refunds_month = (
            db.query(func.coalesce(func.sum(models.ClinicRefund.refund_amount_gnf), 0))
            .filter(
                models.ClinicRefund.clinic_id == clinic_id,
                models.ClinicRefund.status == "paid",
                models.ClinicRefund.paid_at >= start_month,
            )
            .scalar()
            or 0
        )
        revenue_month = int(revenue_month) - int(refunds_month)

        outstanding = (
            db.query(func.count(models.Invoice.id))
            .filter(
                models.Invoice.clinic_id == clinic_id,
                models.Invoice.status.in_(["issued", "partially_paid"]),
            )
            .scalar()
            or 0
        )

        gender_rows = (
            db.query(models.Patient.gender, func.count(models.Patient.id))
            .filter(models.Patient.clinic_id == clinic_id, models.Patient.is_archived.is_(False))
            .group_by(models.Patient.gender)
            .all()
        )
        gender_distribution: dict[str, int] = {"male": 0, "female": 0, "other": 0}
        for g, cnt in gender_rows:
            key = (g or "other").lower()
            if key in ("m", "male", "homme", "h"):
                gender_distribution["male"] += cnt
            elif key in ("f", "female", "femme"):
                gender_distribution["female"] += cnt
            else:
                gender_distribution["other"] += cnt

        dept_rows = (
            db.query(models.Admission.department, func.count(models.Admission.id))
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.department.isnot(None),
                models.Admission.admitted_at >= start_month,
            )
            .group_by(models.Admission.department)
            .all()
        )
        department_distribution = {d or "Non spécifié": c for d, c in dept_rows}

        paid_invoices = (
            db.query(func.count(models.Invoice.id))
            .filter(models.Invoice.clinic_id == clinic_id, models.Invoice.status == "paid")
            .scalar()
            or 0
        )
        refunds_total_gnf = int(refunds_month)

        recent_patients = (
            db.query(models.Patient)
            .filter(models.Patient.clinic_id == clinic_id, models.Patient.is_archived.is_(False))
            .order_by(models.Patient.created_at.desc())
            .limit(8)
            .all()
        )
        recent_admissions = (
            db.query(models.Admission)
            .filter(models.Admission.clinic_id == clinic_id)
            .order_by(models.Admission.created_at.desc())
            .limit(8)
            .all()
        )
        recent_payments = (
            db.query(models.PaymentRecord)
            .join(models.Invoice, models.PaymentRecord.invoice_id == models.Invoice.id)
            .filter(models.Invoice.clinic_id == clinic_id)
            .order_by(models.PaymentRecord.paid_at.desc())
            .limit(8)
            .all()
        )
        recent_refunds = (
            db.query(models.ClinicRefund)
            .filter(models.ClinicRefund.clinic_id == clinic_id)
            .order_by(models.ClinicRefund.created_at.desc())
            .limit(8)
            .all()
        )

        def _patient_label(pid: int) -> str:
            p = db.query(models.Patient).filter(models.Patient.id == pid).first()
            if not p:
                return f"#{pid}"
            num = p.patient_number or f"#{p.id}"
            return f"{num} — {p.last_name} {p.first_name}"

        return {
            "total_patients": total_patients,
            "patients_registered_today": patients_today,
            "admissions_today": admissions_today,
            "hospitalized_patients": hospitalized,
            "paid_invoices": paid_invoices,
            "unpaid_invoices": outstanding,
            "revenue_today_gnf": revenue_today,
            "revenue_month_gnf": revenue_month,
            "refunds_total_gnf": refunds_total_gnf,
            "outstanding_invoices": outstanding,
            "gender_distribution": gender_distribution,
            "department_distribution": department_distribution,
            "recent_registrations": [
                {
                    "patient_id": p.patient_number or f"PAT-{clinic_id:03d}-{p.id:06d}",
                    "patient_name": f"{p.last_name} {p.first_name}",
                    "registered_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in recent_patients
            ],
            "recent_admissions": [
                {
                    "admission_number": a.admission_number,
                    "patient_id": _patient_label(a.patient_id),
                    "department": a.department,
                    "admitted_at": a.admitted_at.isoformat() if a.admitted_at else None,
                }
                for a in recent_admissions
            ],
            "recent_payments": [
                {
                    "invoice_number": (
                        db.query(models.Invoice.invoice_number)
                        .filter(models.Invoice.id == pay.invoice_id)
                        .scalar()
                    ),
                    "amount_gnf": pay.amount_gnf,
                    "payment_method": pay.payment_method,
                    "paid_at": pay.paid_at.isoformat() if pay.paid_at else None,
                }
                for pay in recent_payments
            ],
            "recent_refunds": [
                {
                    "refund_number": r.refund_number,
                    "patient_id": _patient_label(r.patient_id),
                    "refund_amount_gnf": r.refund_amount_gnf,
                    "status": r.status,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                }
                for r in recent_refunds
            ],
        }

    @staticmethod
    def find_invoice(
        db: Session, *, clinic_id: int, query: str, patient_id: int | None = None
    ) -> models.Invoice | None:
        q = query.strip()
        if not q:
            return None
        base = db.query(models.Invoice).options(
            joinedload(models.Invoice.payments), joinedload(models.Invoice.patient)
        ).filter(models.Invoice.clinic_id == clinic_id)
        if patient_id:
            base = base.filter(models.Invoice.patient_id == patient_id)
        if q.isdigit():
            inv = base.filter(models.Invoice.id == int(q)).first()
            if inv:
                return inv
        return base.filter(models.Invoice.invoice_number.ilike(f"%{q}%")).first()

    @staticmethod
    def period_report(
        db: Session, *, clinic_id: int, start: date, end: date
    ) -> dict[str, Any]:
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)

        patients_registered = (
            db.query(func.count(models.Patient.id))
            .filter(
                models.Patient.clinic_id == clinic_id,
                models.Patient.created_at >= start_dt,
                models.Patient.created_at <= end_dt,
            )
            .scalar()
            or 0
        )
        admissions = (
            db.query(func.count(models.Admission.id))
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.admitted_at >= start_dt,
                models.Admission.admitted_at <= end_dt,
            )
            .scalar()
            or 0
        )
        hospitalizations = (
            db.query(func.count(models.Admission.id))
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.admission_type == "hospitalization",
                models.Admission.admitted_at >= start_dt,
                models.Admission.admitted_at <= end_dt,
            )
            .scalar()
            or 0
        )
        invoices_paid = (
            db.query(func.count(models.Invoice.id))
            .filter(
                models.Invoice.clinic_id == clinic_id,
                models.Invoice.status == "paid",
                models.Invoice.paid_at >= start_dt,
                models.Invoice.paid_at <= end_dt,
            )
            .scalar()
            or 0
        )
        invoices_unpaid = (
            db.query(func.count(models.Invoice.id))
            .filter(
                models.Invoice.clinic_id == clinic_id,
                models.Invoice.status.in_(["issued", "partially_paid"]),
                models.Invoice.issued_at >= start_dt,
                models.Invoice.issued_at <= end_dt,
            )
            .scalar()
            or 0
        )
        payments_received = (
            db.query(func.coalesce(func.sum(models.PaymentRecord.amount_gnf), 0))
            .join(models.Invoice, models.PaymentRecord.invoice_id == models.Invoice.id)
            .filter(
                models.Invoice.clinic_id == clinic_id,
                models.PaymentRecord.paid_at >= start_dt,
                models.PaymentRecord.paid_at <= end_dt,
            )
            .scalar()
            or 0
        )
        refunds_paid = (
            db.query(func.coalesce(func.sum(models.ClinicRefund.refund_amount_gnf), 0))
            .filter(
                models.ClinicRefund.clinic_id == clinic_id,
                models.ClinicRefund.status == "paid",
                models.ClinicRefund.paid_at >= start_dt,
                models.ClinicRefund.paid_at <= end_dt,
            )
            .scalar()
            or 0
        )
        revenue_by_service_rows = (
            db.query(models.Invoice.department, func.coalesce(func.sum(models.PaymentRecord.amount_gnf), 0))
            .join(models.PaymentRecord, models.PaymentRecord.invoice_id == models.Invoice.id)
            .filter(
                models.Invoice.clinic_id == clinic_id,
                models.PaymentRecord.paid_at >= start_dt,
                models.PaymentRecord.paid_at <= end_dt,
            )
            .group_by(models.Invoice.department)
            .all()
        )
        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "patients_registered": patients_registered,
            "admissions": admissions,
            "hospitalizations": hospitalizations,
            "invoices_paid": invoices_paid,
            "invoices_unpaid": invoices_unpaid,
            "payments_received_gnf": int(payments_received),
            "refunds_gnf": int(refunds_paid),
            "net_revenue_gnf": int(payments_received) - int(refunds_paid),
            "revenue_by_service": {d or "Non spécifié": int(v) for d, v in revenue_by_service_rows},
        }

    @staticmethod
    def export_report_csv(report: dict[str, Any]) -> str:
        lines = [
            "Indicateur,Valeur",
            f"Période,{report['period_start']} → {report['period_end']}",
            f"Patients enregistrés,{report['patients_registered']}",
            f"Admissions,{report['admissions']}",
            f"Hospitalisations,{report['hospitalizations']}",
            f"Factures payées,{report['invoices_paid']}",
            f"Factures impayées,{report['invoices_unpaid']}",
            f"Paiements reçus (GNF),{report['payments_received_gnf']}",
            f"Remboursements (GNF),{report['refunds_gnf']}",
            f"Recettes nettes (GNF),{report['net_revenue_gnf']}",
            "",
            "Service,Recettes (GNF)",
        ]
        for svc, amt in (report.get("revenue_by_service") or {}).items():
            lines.append(f"{svc},{amt}")
        return "\n".join(lines)

    @staticmethod
    def _service_request_number(clinic_id: int, request_id: int) -> str:
        return f"DSR-{clinic_id:03d}-{request_id:06d}"

    @staticmethod
    def _serialize_service_request(row: models.ClinicServiceRequest) -> dict[str, Any]:
        patient_name = None
        patient_number = None
        if row.patient:
            patient_name = f"{row.patient.last_name} {row.patient.first_name}".strip()
            patient_number = row.patient.patient_number
        return {
            "id": row.id,
            "request_number": row.request_number,
            "patient_id": row.patient_id,
            "patient_name": patient_name,
            "patient_number": patient_number,
            "admission_id": row.admission_id,
            "service_category": row.service_category,
            "service_name": row.service_name,
            "department": row.department,
            "status": row.status,
            "notes": row.notes,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }

    @staticmethod
    def list_service_requests(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int | None = None,
        q: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[models.ClinicServiceRequest]:
        query = (
            db.query(models.ClinicServiceRequest)
            .options(joinedload(models.ClinicServiceRequest.patient))
            .filter(models.ClinicServiceRequest.clinic_id == clinic_id)
        )
        if patient_id:
            query = query.filter(models.ClinicServiceRequest.patient_id == patient_id)
        if status:
            query = query.filter(models.ClinicServiceRequest.status == status)
        if q and q.strip():
            pattern = f"%{q.strip()}%"
            query = query.filter(
                models.ClinicServiceRequest.service_name.ilike(pattern)
                | models.ClinicServiceRequest.request_number.ilike(pattern)
                | models.ClinicServiceRequest.department.ilike(pattern)
            )
        return query.order_by(models.ClinicServiceRequest.created_at.desc()).limit(limit).all()

    @staticmethod
    def create_service_request(
        db: Session,
        *,
        clinic_id: int,
        payload: ServiceRequestCreate,
        actor: User,
    ) -> models.ClinicServiceRequest:
        from core.tenant import assert_patient_in_clinic

        assert_patient_in_clinic(db, patient_id=payload.patient_id, clinic_id=clinic_id)
        row = models.ClinicServiceRequest(
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            admission_id=payload.admission_id,
            request_number="PENDING",
            service_category=payload.service_category,
            service_name=payload.service_name.strip(),
            department=(payload.department or "").strip() or None,
            status=payload.status,
            notes=(payload.notes or "").strip() or None,
            created_by_user_id=actor.id,
            updated_by_user_id=actor.id,
        )
        db.add(row)
        db.flush()
        row.request_number = ReceptionHisService._service_request_number(clinic_id, row.id)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def update_service_request(
        db: Session,
        *,
        clinic_id: int,
        request_id: int,
        payload: ServiceRequestUpdate,
        actor: User,
    ) -> models.ClinicServiceRequest:
        row = (
            db.query(models.ClinicServiceRequest)
            .options(joinedload(models.ClinicServiceRequest.patient))
            .filter(
                models.ClinicServiceRequest.id == request_id,
                models.ClinicServiceRequest.clinic_id == clinic_id,
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Demande de service introuvable")
        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            if key in ("service_name", "department", "notes") and isinstance(value, str):
                value = value.strip() or None
            setattr(row, key, value)
        row.updated_by_user_id = actor.id
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def delete_service_request(db: Session, *, clinic_id: int, request_id: int) -> None:
        row = (
            db.query(models.ClinicServiceRequest)
            .filter(
                models.ClinicServiceRequest.id == request_id,
                models.ClinicServiceRequest.clinic_id == clinic_id,
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=404, detail="Demande de service introuvable")
        db.delete(row)
        db.commit()

    @staticmethod
    def dashboard_queue(db: Session, *, clinic_id: int, bucket: str) -> list[dict[str, Any]]:
        today = date.today()
        month_start = today.replace(day=1)
        start_today = datetime.combine(today, time.min)
        end_today = datetime.combine(today, time.max)
        start_month = datetime.combine(month_start, time.min)

        def gender_label(g: str | None) -> str:
            if not g:
                return "—"
            key = g.lower()
            if key in ("m", "male", "homme", "h"):
                return "Masculin"
            if key in ("f", "female", "femme"):
                return "Féminin"
            return g

        if bucket == "total_patients":
            rows = (
                db.query(models.Patient)
                .filter(models.Patient.clinic_id == clinic_id, models.Patient.is_archived.is_(False))
                .order_by(models.Patient.created_at.desc())
                .limit(500)
                .all()
            )
            return [
                {
                    "patient_id": p.id,
                    "patient_name": f"{p.last_name} {p.first_name}",
                    "patient_number": p.patient_number,
                    "phone": p.phone,
                    "gender": gender_label(p.gender),
                    "registration_date": p.registration_date.isoformat() if p.registration_date else (
                        p.created_at.date().isoformat() if p.created_at else None
                    ),
                }
                for p in rows
            ]

        if bucket == "patients_registered_today":
            rows = (
                db.query(models.Patient)
                .filter(
                    models.Patient.clinic_id == clinic_id,
                    models.Patient.is_archived.is_(False),
                    models.Patient.created_at >= start_today,
                    models.Patient.created_at <= end_today,
                )
                .order_by(models.Patient.created_at.desc())
                .all()
            )
            return [
                {
                    "patient_id": p.id,
                    "patient_name": f"{p.last_name} {p.first_name}",
                    "patient_number": p.patient_number,
                    "phone": p.phone,
                    "gender": gender_label(p.gender),
                    "registration_date": p.created_at.isoformat() if p.created_at else None,
                }
                for p in rows
            ]

        if bucket == "admissions_today":
            rows = (
                db.query(models.Admission)
                .options(joinedload(models.Admission.patient))
                .filter(
                    models.Admission.clinic_id == clinic_id,
                    models.Admission.admitted_at >= start_today,
                    models.Admission.admitted_at <= end_today,
                )
                .order_by(models.Admission.admitted_at.desc())
                .all()
            )
            return [
                {
                    "admission_id": a.id,
                    "patient_id": a.patient_id,
                    "patient_name": (
                        f"{a.patient.last_name} {a.patient.first_name}" if a.patient else f"#{a.patient_id}"
                    ),
                    "admitted_at": a.admitted_at.isoformat() if a.admitted_at else None,
                    "department": a.department,
                    "status": a.status,
                }
                for a in rows
            ]

        if bucket == "hospitalized_patients":
            rows = (
                db.query(models.Admission)
                .options(
                    joinedload(models.Admission.patient),
                    joinedload(models.Admission.stays).joinedload(models.PatientStay.bed).joinedload(
                        models.HospitalBed.room
                    ),
                )
                .filter(
                    models.Admission.clinic_id == clinic_id,
                    models.Admission.admission_type == "hospitalization",
                    models.Admission.status.in_(["admitted", "in_care", "pending"]),
                )
                .order_by(models.Admission.admitted_at.desc())
                .all()
            )
            out = []
            for a in rows:
                room_label = "—"
                current_stay = next((s for s in (a.stays or []) if s.is_current and not s.released_at), None)
                if current_stay and current_stay.bed and current_stay.bed.room:
                    room_label = f"{current_stay.bed.room.ward_name} — {current_stay.bed.room.room_number}/{current_stay.bed.bed_number}"
                doctor_name = "—"
                if a.attending_clinician_user_id:
                    doc = db.query(models.User).filter(models.User.id == a.attending_clinician_user_id).first()
                    if doc:
                        doctor_name = doc.email or f"#{doc.id}"
                out.append(
                    {
                        "admission_id": a.id,
                        "patient_id": a.patient_id,
                        "patient_name": (
                            f"{a.patient.last_name} {a.patient.first_name}" if a.patient else f"#{a.patient_id}"
                        ),
                        "room": room_label,
                        "doctor_name": doctor_name,
                        "admitted_at": a.admitted_at.isoformat() if a.admitted_at else None,
                    }
                )
            return out

        if bucket == "paid_invoices":
            rows = (
                db.query(models.Invoice)
                .options(joinedload(models.Invoice.patient), joinedload(models.Invoice.payments))
                .filter(models.Invoice.clinic_id == clinic_id, models.Invoice.status == "paid")
                .order_by(models.Invoice.issued_at.desc())
                .limit(200)
                .all()
            )
            return [
                {
                    "invoice_id": inv.id,
                    "patient_id": inv.patient_id,
                    "patient_name": (
                        f"{inv.patient.last_name} {inv.patient.first_name}" if inv.patient else f"#{inv.patient_id}"
                    ),
                    "invoice_number": inv.invoice_number,
                    "amount_gnf": inv.total_amount_gnf,
                    "payment_method": inv.payments[-1].payment_method if inv.payments else "—",
                    "paid_at": inv.payments[-1].paid_at.isoformat() if inv.payments else None,
                }
                for inv in rows
            ]

        if bucket == "unpaid_invoices":
            rows = (
                db.query(models.Invoice)
                .options(joinedload(models.Invoice.patient))
                .filter(
                    models.Invoice.clinic_id == clinic_id,
                    models.Invoice.status.in_(["issued", "partially_paid", "unpaid"]),
                )
                .order_by(models.Invoice.issued_at.desc())
                .limit(200)
                .all()
            )
            return [
                {
                    "invoice_id": inv.id,
                    "patient_id": inv.patient_id,
                    "patient_name": (
                        f"{inv.patient.last_name} {inv.patient.first_name}" if inv.patient else f"#{inv.patient_id}"
                    ),
                    "invoice_number": inv.invoice_number,
                    "outstanding_balance_gnf": max(0, inv.total_amount_gnf - inv.paid_amount_gnf),
                    "issued_at": inv.issued_at.isoformat() if inv.issued_at else None,
                }
                for inv in rows
            ]

        if bucket == "revenue_today":
            rows = (
                db.query(models.PaymentRecord)
                .join(models.Invoice, models.PaymentRecord.invoice_id == models.Invoice.id)
                .options(joinedload(models.PaymentRecord.invoice).joinedload(models.Invoice.patient))
                .filter(
                    models.Invoice.clinic_id == clinic_id,
                    models.PaymentRecord.paid_at >= start_today,
                    models.PaymentRecord.paid_at <= end_today,
                )
                .order_by(models.PaymentRecord.paid_at.desc())
                .all()
            )
            return [
                {
                    "payment_id": pay.id,
                    "invoice_id": pay.invoice_id,
                    "invoice_number": pay.invoice.invoice_number if pay.invoice else None,
                    "patient_name": (
                        f"{pay.invoice.patient.last_name} {pay.invoice.patient.first_name}"
                        if pay.invoice and pay.invoice.patient
                        else "—"
                    ),
                    "amount_gnf": pay.amount_gnf,
                    "payment_method": pay.payment_method,
                    "paid_at": pay.paid_at.isoformat() if pay.paid_at else None,
                }
                for pay in rows
            ]

        if bucket == "revenue_month":
            rows = (
                db.query(models.PaymentRecord)
                .join(models.Invoice, models.PaymentRecord.invoice_id == models.Invoice.id)
                .options(joinedload(models.PaymentRecord.invoice).joinedload(models.Invoice.patient))
                .filter(
                    models.Invoice.clinic_id == clinic_id,
                    models.PaymentRecord.paid_at >= start_month,
                )
                .order_by(models.PaymentRecord.paid_at.desc())
                .limit(500)
                .all()
            )
            return [
                {
                    "payment_id": pay.id,
                    "invoice_id": pay.invoice_id,
                    "invoice_number": pay.invoice.invoice_number if pay.invoice else None,
                    "patient_name": (
                        f"{pay.invoice.patient.last_name} {pay.invoice.patient.first_name}"
                        if pay.invoice and pay.invoice.patient
                        else "—"
                    ),
                    "amount_gnf": pay.amount_gnf,
                    "payment_method": pay.payment_method,
                    "paid_at": pay.paid_at.isoformat() if pay.paid_at else None,
                }
                for pay in rows
            ]

        if bucket == "refunds":
            rows = (
                db.query(models.ClinicRefund)
                .options(joinedload(models.ClinicRefund.patient), joinedload(models.ClinicRefund.invoice))
                .filter(models.ClinicRefund.clinic_id == clinic_id)
                .order_by(models.ClinicRefund.created_at.desc())
                .limit(200)
                .all()
            )
            return [
                {
                    "refund_id": r.id,
                    "refund_number": r.refund_number,
                    "patient_id": r.patient_id,
                    "patient_name": (
                        f"{r.patient.last_name} {r.patient.first_name}" if r.patient else f"#{r.patient_id}"
                    ),
                    "invoice_number": r.invoice.invoice_number if r.invoice else None,
                    "refund_amount_gnf": r.refund_amount_gnf,
                    "reason": r.reason,
                    "status": r.status,
                    "refund_method": r.refund_method,
                    "created_at": r.created_at.isoformat() if r.created_at else None,
                    "paid_at": r.paid_at.isoformat() if r.paid_at else None,
                }
                for r in rows
            ]

        raise HTTPException(status_code=400, detail=f"Bucket inconnu: {bucket}")
