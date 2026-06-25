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


def _admission_number(db: Session, clinic_id: int) -> str:
    count = db.query(models.Admission).filter(models.Admission.clinic_id == clinic_id).count()
    year = datetime.utcnow().year
    return f"ADM-{year}-{clinic_id:03d}-{count + 1:05d}"


def _invoice_number(db: Session, clinic_id: int) -> str:
    count = db.query(models.Invoice).filter(models.Invoice.clinic_id == clinic_id).count()
    year = datetime.utcnow().year
    return f"INV-{year}-{clinic_id:03d}-{count + 1:05d}"


def _refund_number(db: Session, clinic_id: int) -> str:
    count = db.query(models.ClinicRefund).filter(models.ClinicRefund.clinic_id == clinic_id).count()
    year = datetime.utcnow().year
    return f"RFD-{year}-{clinic_id:03d}-{count + 1:05d}"


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
                    "matches": [m.model_dump() for m in dupes],
                },
            )

        age = _calc_age(payload.date_of_birth)
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

        status = "admitted" if payload.admission_type == "hospitalization" else "pending"
        if payload.admission_type == "emergency":
            status = "in_care"

        admission = models.Admission(
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            admission_number=_admission_number(db, clinic_id),
            department=payload.department.strip(),
            admission_type=payload.admission_type,
            status=status,
            attending_clinician_user_id=payload.attending_clinician_user_id,
            notes=payload.notes or payload.attending_physician_name,
            admitted_by_user_id=actor.id,
            admitted_at=admitted_at,
        )
        db.add(admission)
        db.commit()
        db.refresh(admission)
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

        assert_patient_in_clinic(db, patient_id=payload.patient_id, clinic_id=clinic_id)
        invoice = models.Invoice(
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            invoice_number=_invoice_number(db, clinic_id),
            department=payload.department.strip(),
            status="issued",
            total_amount_gnf=payload.total_amount_gnf,
            paid_amount_gnf=0,
            issued_at=datetime.utcnow(),
            created_by_user_id=actor.id,
        )
        db.add(invoice)
        db.flush()
        item = models.InvoiceItem(
            invoice_id=invoice.id,
            charge_type="procedure",
            source_type="reception",
            source_id=invoice.id,
            description=payload.description.strip(),
            quantity=1,
            unit_price_gnf=payload.total_amount_gnf,
            amount_gnf=payload.total_amount_gnf,
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
    def list_refunds(db: Session, *, clinic_id: int) -> list[models.ClinicRefund]:
        return (
            db.query(models.ClinicRefund)
            .options(joinedload(models.ClinicRefund.patient), joinedload(models.ClinicRefund.invoice))
            .filter(models.ClinicRefund.clinic_id == clinic_id)
            .order_by(models.ClinicRefund.created_at.desc())
            .limit(100)
            .all()
        )

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

        return {
            "total_patients": total_patients,
            "patients_registered_today": patients_today,
            "admissions_today": admissions_today,
            "hospitalized_patients": hospitalized,
            "revenue_today_gnf": revenue_today,
            "revenue_month_gnf": revenue_month,
            "outstanding_invoices": outstanding,
            "gender_distribution": gender_distribution,
            "department_distribution": department_distribution,
        }
