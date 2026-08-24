"""Reception HIS — registration, admission, billing, refunds, dashboard."""

from __future__ import annotations

import json
import hashlib
import uuid
from datetime import date, datetime, time
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

import models
from models.user import User
from schemas.reception_his import (
    DuplicateCheckRequest,
    DuplicatePatientMatch,
    PatientRegistrationCreate,
    PatientRegistrationUpdate,
    ReceptionAdmissionCreate,
    ReceptionInvoiceCreate,
    ReceptionPaymentCreate,
    RefundCreate,
    RefundStatusUpdate,
    ServiceRequestCreate,
    ServiceRequestUpdate,
)
from core.patient_number import format_patient_number
from services.cis_audit import log_cis
from services.medical_history_service import ensure_medical_record


def _calc_age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def _normalize_phone(phone: str | None) -> str:
    if not phone:
        return ""
    return "".join(c for c in phone if c.isdigit())[-9:]


def _registration_dedupe_key(clinic_id: int, payload: PatientRegistrationCreate) -> str:
    identity = "|".join(
        (
            str(clinic_id),
            _normalize_phone(payload.phone),
            payload.first_name.strip().casefold(),
            payload.last_name.strip().casefold(),
            payload.date_of_birth.isoformat() if payload.date_of_birth else "",
        )
    )
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()


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


def _department_price_context(department: str | None) -> str | None:
    """Map invoice department to allowed specialty price_variant context."""
    d = (department or "").strip().lower()
    if not d:
        return None
    if "urgence" in d:
        return "emergency"
    # Match spécialisée / specialisee / specialized
    if "sp" in d and "cialis" in d:
        return "specialized"
    if "specialized" in d:
        return "specialized"
    return None


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
            age_value = age
            age_unit = "years"
        else:
            age_value = payload.age_value if payload.age_value is not None else payload.age_years
            age_unit = payload.age_unit
            age = age_value if age_unit == "years" else 0
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

        # PostgreSQL enforces NOT NULL on INSERT (Alembic 0028). Allocate a unique
        # provisional dossier number before flush, then replace with the canonical
        # PAT-{clinic}-{id} once the primary key is known — single commit, never NULL.
        provisional_number = f"TMP-{clinic_id}-{uuid.uuid4().hex[:16].upper()}"
        dedupe_key = None if payload.confirm_duplicate else _registration_dedupe_key(clinic_id, payload)

        patient = models.Patient(
            clinic_id=clinic_id,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            age=age,
            age_value=age_value,
            age_unit=age_unit,
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
            patient_number=provisional_number,
            registration_dedupe_key=dedupe_key,
            is_newborn=bool(payload.is_newborn),
            registration_date=payload.registration_date,
        )
        db.add(patient)
        # Single commit: flush to allocate id, assign canonical dossier number, then commit once.
        try:
            db.flush()
        except IntegrityError as error:
            db.rollback()
            if dedupe_key:
                existing = (
                    db.query(models.Patient)
                    .filter(
                        models.Patient.clinic_id == clinic_id,
                        models.Patient.registration_dedupe_key == dedupe_key,
                        models.Patient.is_archived.is_(False),
                    )
                    .first()
                )
                if existing:
                    raise HTTPException(
                        status_code=409,
                        detail={
                            "code": "duplicate_patient",
                            "message": "Ce patient vient d’être enregistré sur un autre appareil",
                            "matches": [
                                DuplicatePatientMatch(
                                    id=existing.id,
                                    patient_number=existing.patient_number,
                                    first_name=existing.first_name,
                                    last_name=existing.last_name,
                                    phone=existing.phone,
                                    date_of_birth=existing.date_of_birth,
                                    match_reasons=["concurrent_registration"],
                                ).model_dump(mode="json")
                            ],
                        },
                    ) from error
            raise
        patient.patient_number = format_patient_number(clinic_id, patient.id)
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
    def update_patient(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        payload: PatientRegistrationUpdate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.Patient:
        patient = db.query(models.Patient).filter(
            models.Patient.id == patient_id,
            models.Patient.clinic_id == clinic_id,
            models.Patient.is_archived.is_(False),
        ).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient introuvable")

        if payload.date_of_birth:
            age = _calc_age(payload.date_of_birth)
            age_value, age_unit = age, "years"
        else:
            age_value = payload.age_value if payload.age_value is not None else payload.age_years
            age_unit = payload.age_unit
            age = age_value if age_unit == "years" else 0

        emergency = payload.emergency_contact.model_dump()
        if payload.emergency_contact.same_address_as_patient:
            emergency.update(address=payload.address, commune=payload.commune,
                             region=payload.region, country=payload.country)
        payer = payload.payer
        if payer.payer_type == "insurance" and not payer.insurance_company:
            raise HTTPException(status_code=400, detail="Assurance : nom de la compagnie requis")
        if payer.payer_type == "company" and not payer.company_name:
            raise HTTPException(status_code=400, detail="Entreprise : nom requis")

        scalar = {
            "first_name": payload.first_name.strip(), "last_name": payload.last_name.strip(),
            "gender": payload.gender, "date_of_birth": payload.date_of_birth,
            "date_of_birth_precision": payload.date_of_birth_precision, "age": age,
            "age_value": age_value, "age_unit": age_unit, "phone": payload.phone.strip(),
            "phone_secondary": (payload.phone_secondary or "").strip() or None,
            "email": (payload.email or "").strip() or None, "address": payload.address.strip(),
            "commune": (payload.commune or "").strip() or None, "city": (payload.city or "").strip() or None,
            "region": (payload.region or "").strip() or None, "country": (payload.country or "").strip() or None,
            "place_of_birth": (payload.place_of_birth or "").strip() or None,
            "nationality": (payload.nationality or "").strip() or None,
            "marital_status": (payload.marital_status or "").strip() or None,
            "preferred_language": (payload.preferred_language or "").strip() or None,
            "photo_url": (payload.photo_url or "").strip() or None,
            "mother_first_name": (payload.mother_first_name or "").strip() or None,
            "mother_last_name": (payload.mother_last_name or "").strip() or None,
            "profession": (payload.profession or "").strip() or None,
            "emergency_contact": payload.emergency_contact.full_name,
            "emergency_contact_json": json.dumps(emergency, ensure_ascii=False),
            "payer_json": json.dumps(payer.model_dump(), ensure_ascii=False),
            "is_newborn": bool(payload.is_newborn), "registration_date": payload.registration_date,
        }
        scalar["mother_name"] = " ".join(filter(None, (scalar["mother_first_name"], scalar["mother_last_name"]))) or None
        for name, value in scalar.items():
            setattr(patient, name, value)
        db.commit()
        db.refresh(patient)
        if actor:
            log_cis(db, actor=actor, clinic_id=clinic_id, patient_id=patient.id,
                    action="update", resource_type="patient", resource_id=patient.id,
                    client_ip=client_ip)
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

        is_hospitalization = payload.admission_type == "hospitalization" or "Hospitalisation" in payload.services
        if is_hospitalization:
            existing = (
                db.query(models.Admission)
                .filter(
                    models.Admission.patient_id == payload.patient_id,
                    models.Admission.clinic_id == clinic_id,
                    models.Admission.services_json.contains("Hospitalisation")
                    | (models.Admission.admission_type == "hospitalization"),
                    models.Admission.status.notin_(["discharged", "cancelled"]),
                )
                .first()
            )
            if existing:
                raise HTTPException(status_code=409, detail="Hospitalisation active déjà en cours")
            placement_filter = None
            if payload.bed_number:
                placement_filter = models.Admission.bed_number == payload.bed_number
            elif payload.cabin_number:
                placement_filter = models.Admission.cabin_number == payload.cabin_number
            if placement_filter is not None:
                occupied = db.query(models.Admission).filter(
                    models.Admission.clinic_id == clinic_id,
                    models.Admission.services_json.contains("Hospitalisation")
                    | (models.Admission.admission_type == "hospitalization"),
                    models.Admission.status.in_(["pending", "admitted", "in_care", "transferred"]),
                    placement_filter,
                ).first()
                if occupied:
                    label = f"Lit n° {payload.bed_number}" if payload.bed_number else f"Cabine n° {payload.cabin_number}"
                    raise HTTPException(status_code=409, detail=f"{label} déjà occupé")

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
            bed_number=payload.bed_number,
            cabin_number=payload.cabin_number,
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
    def _resolve_invoice_line(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        row,
        seen_dsr_ids: set[int],
        actor: User,
        department: str | None = None,
    ) -> dict:
        """Build one invoice line. Prices are server-authoritative."""
        from core.rbac import Permission, assert_permission
        from data.aasma_billing_catalog import resolve_billing_catalog_item

        source_type = (row.source_type or "reception").strip() or "reception"
        source_ref = (getattr(row, "source_ref", None) or "").strip()
        quantity = max(1, int(row.quantity or 1))
        catalog_code = (getattr(row, "catalog_code", None) or "").strip() or None
        override_reason = (getattr(row, "price_override_reason", None) or "").strip()
        client_unit = getattr(row, "unit_price_gnf", None)
        dept_context = _department_price_context(department)

        # --- Service request (DSR) path ---
        if source_type == "service_request" or source_ref.upper().startswith("DSR-"):
            dsr = ReceptionHisService.get_service_request_by_number(
                db, clinic_id=clinic_id, request_number=source_ref or str(getattr(row, "source_ref", "") or "")
            )
            if dsr.patient_id != patient_id:
                raise HTTPException(
                    status_code=400,
                    detail=f"La demande {dsr.request_number} n'appartient pas à ce patient",
                )
            if dsr.status == "cancelled":
                raise HTTPException(
                    status_code=400,
                    detail=f"Demande {dsr.request_number} annulée — facturation refusée",
                )
            if dsr.id in seen_dsr_ids:
                raise HTTPException(
                    status_code=409,
                    detail=f"Demande {dsr.request_number} déjà présente sur cette facture",
                )
            already = (
                db.query(models.InvoiceItem)
                .join(models.Invoice, models.Invoice.id == models.InvoiceItem.invoice_id)
                .filter(
                    models.InvoiceItem.source_type == "service_request",
                    models.InvoiceItem.source_id == dsr.id,
                    models.Invoice.clinic_id == clinic_id,
                    models.Invoice.status != "cancelled",
                )
                .first()
            )
            if already:
                raise HTTPException(
                    status_code=409,
                    detail=f"Demande {dsr.request_number} déjà facturée",
                )
            seen_dsr_ids.add(dsr.id)
            if dsr.service_category == "hospitalization":
                quantity = int(getattr(dsr, "quantity", 1) or 1)
            # Prefer catalog re-resolve; otherwise trust DSR stored price (already privilege-gated).
            unit = int(dsr.unit_price_gnf or 0)
            code = catalog_code or dsr.catalog_code
            if code:
                cat = resolve_billing_catalog_item(code)
                if cat:
                    unit = int(cat["price_gnf"])
            return {
                "charge_type": dsr.charge_type or getattr(row, "charge_type", None) or "procedure",
                "description": f"{dsr.service_name} [{dsr.request_number}]",
                "quantity": quantity,
                "unit_price_gnf": unit,
                "amount_gnf": unit * quantity,
                "source_type": "service_request",
                "source_id": dsr.id,
                "service_request": dsr,
                "price_audit": None,
            }

        # --- Catalog-authoritative manual line ---
        description = (getattr(row, "description", None) or "").strip()
        charge_type = getattr(row, "charge_type", None)
        price_audit = None

        if catalog_code:
            price_variant = (getattr(row, "price_variant", None) or "").strip().lower() or None
            if price_variant not in ("specialized", "emergency"):
                # Infer from structured department only — never from free-text description.
                price_variant = dept_context

            # Specialty tariff selection must match invoice department context.
            # A client must not pick emergency (cheaper) under a specialized department
            # without an explicit privileged override + audit reason.
            if price_variant in ("emergency", "specialized"):
                if dept_context and price_variant != dept_context:
                    if override_reason:
                        assert_permission(actor, Permission.BILLING_OVERRIDE)
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"price_variant={price_variant!r} incompatible avec "
                                f"department={department!r}. Utilisez le service "
                                f"correspondant, ou fournissez price_override_reason "
                                f"avec le droit billing.override."
                            ),
                        )
                elif not dept_context and price_variant == "emergency":
                    # Emergency tariff requires an emergency department classification.
                    if override_reason:
                        assert_permission(actor, Permission.BILLING_OVERRIDE)
                    else:
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                "price_variant='emergency' requiert un department "
                                "d'urgences (ex. 'Consultation urgences')."
                            ),
                        )

            cat = resolve_billing_catalog_item(catalog_code, price_variant=price_variant)
            if not cat:
                raise HTTPException(status_code=400, detail=f"Code catalogue inconnu: {catalog_code}")
            description = cat["label"]
            charge_type = cat["charge_type"]
            catalog_price = int(cat["price_gnf"])
            if override_reason:
                assert_permission(actor, Permission.BILLING_OVERRIDE)
                if client_unit is None and cat.get("bucket") != "specialty":
                    # Numeric override still requires a client unit price.
                    raise HTTPException(
                        status_code=400,
                        detail="unit_price_gnf requis avec price_override_reason",
                    )
                if client_unit is not None:
                    unit = int(client_unit)
                else:
                    # Variant/classification override keeps catalog price for that variant.
                    unit = catalog_price
                price_audit = {
                    "kind": "price_override",
                    "catalog_code": catalog_code,
                    "catalog_price_gnf": catalog_price,
                    "negotiated_price_gnf": unit,
                    "reason": override_reason,
                    "price_variant": cat.get("price_variant") or price_variant,
                    "department": department,
                    "department_context": dept_context,
                }
            else:
                unit = catalog_price
        else:
            # Free-text non-catalog line — privilege + reason required.
            assert_permission(actor, Permission.BILLING_FREE_TEXT)
            if client_unit is None:
                raise HTTPException(
                    status_code=400,
                    detail="unit_price_gnf requis pour ligne hors catalogue",
                )
            if not override_reason:
                raise HTTPException(
                    status_code=400,
                    detail="price_override_reason requis pour ligne hors catalogue",
                )
            if not description:
                raise HTTPException(status_code=400, detail="description requise pour ligne hors catalogue")
            if not charge_type:
                raise HTTPException(status_code=400, detail="charge_type requis pour ligne hors catalogue")
            unit = int(client_unit)
            price_audit = {
                "kind": "free_text_charge",
                "negotiated_price_gnf": unit,
                "reason": override_reason,
            }

        return {
            "charge_type": charge_type,
            "description": description,
            "quantity": quantity,
            "unit_price_gnf": unit,
            "amount_gnf": unit * quantity,
            "source_type": source_type,
            "source_id": None,
            "service_request": None,
            "price_audit": price_audit,
        }

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

        if not payload.items:
            raise HTTPException(
                status_code=400,
                detail="items[] requis — facturation legacy (total_amount_gnf) refusée",
            )

        line_payloads = []
        billed_requests: list[models.ClinicServiceRequest] = []
        seen_dsr_ids: set[int] = set()
        price_audits: list[dict] = []
        for row in payload.items:
            line = ReceptionHisService._resolve_invoice_line(
                db,
                clinic_id=clinic_id,
                patient_id=payload.patient_id,
                row=row,
                seen_dsr_ids=seen_dsr_ids,
                actor=actor,
                department=payload.department,
            )
            if line.get("service_request") is not None:
                billed_requests.append(line["service_request"])
            if line.get("price_audit"):
                price_audits.append(line["price_audit"])
            line_payloads.append(line)

        subtotal = sum(int(l["amount_gnf"]) for l in line_payloads)
        exemption_percent = float(payload.exemption_percent or 0)
        if exemption_percent > 0:
            from core.rbac import Permission, assert_permission

            # Invoice write-offs / exemptions are privileged — never receptionist/cashier self-serve.
            assert_permission(actor, Permission.BILLING_OVERRIDE)
            if not (getattr(payload, "exemption_reason", None) or "").strip():
                raise HTTPException(
                    status_code=400,
                    detail="exemption_reason est requis lorsque exemption_percent > 0",
                )
        exemption_amount = int(subtotal * exemption_percent / 100)
        net_total = max(0, subtotal - exemption_amount)

        notes = None
        if exemption_percent > 0:
            notes = f"Exemption {exemption_percent:g}% — {(payload.exemption_reason or '').strip()}"

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
            notes=notes,
            issued_at=issued_at,
            created_by_user_id=actor.id,
        )
        db.add(invoice)
        db.flush()
        for idx, line in enumerate(line_payloads):
            source_id = line.get("source_id")
            if source_id is None:
                source_id = invoice.id * 1000 + idx
            item = models.InvoiceItem(
                invoice_id=invoice.id,
                charge_type=line["charge_type"],
                source_type=line["source_type"],
                source_id=int(source_id),
                description=line["description"],
                quantity=line["quantity"],
                unit_price_gnf=line["unit_price_gnf"],
                amount_gnf=line["amount_gnf"],
            )
            db.add(item)
        for dsr in billed_requests:
            dsr.status = "completed"
            dsr.updated_by_user_id = actor.id
            db.add(dsr)
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            from sqlalchemy.exc import IntegrityError

            if isinstance(exc, IntegrityError):
                raise HTTPException(
                    status_code=409,
                    detail="Conflit de facturation (demande déjà facturée)",
                ) from exc
            raise
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
        for audit in price_audits:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=payload.patient_id,
                action=audit["kind"],
                resource_type="invoice_price",
                resource_id=invoice.id,
                client_ip=client_ip,
            )
            # Persist structured reason in invoice notes for forensic review.
            detail = (
                f"{audit['kind']}: {audit.get('reason', '')} "
                f"catalog={audit.get('catalog_code')} "
                f"catalog_price={audit.get('catalog_price_gnf')} "
                f"negotiated={audit.get('negotiated_price_gnf')}"
            ).strip()
            invoice.notes = f"{(invoice.notes + ' | ') if invoice.notes else ''}{detail}"
        if price_audits:
            db.add(invoice)
            db.commit()
            db.refresh(invoice)
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
                joinedload(models.Invoice.created_by_user),
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
            .options(
                joinedload(models.Invoice.payments),
                joinedload(models.Invoice.patient),
                joinedload(models.Invoice.items),
                joinedload(models.Invoice.created_by_user),
            )
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
            joinedload(models.Invoice.payments),
            joinedload(models.Invoice.patient),
            joinedload(models.Invoice.created_by_user),
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
            "catalog_code": getattr(row, "catalog_code", None),
            "charge_type": getattr(row, "charge_type", None),
            "unit_price_gnf": getattr(row, "unit_price_gnf", None),
            "quantity": getattr(row, "quantity", 1) or 1,
            "duration_value": getattr(row, "duration_value", None),
            "duration_unit": getattr(row, "duration_unit", None),
            "specialty_code": getattr(row, "specialty_code", None),
            "accommodation_type": getattr(row, "accommodation_type", None),
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
        from data.aasma_billing_catalog import resolve_billing_catalog_item

        assert_patient_in_clinic(db, patient_id=payload.patient_id, clinic_id=clinic_id)

        from core.rbac import Permission, assert_permission

        catalog_code = (payload.catalog_code or "").strip() or None
        service_name = (payload.service_name or "").strip()
        charge_type = (payload.charge_type or "").strip() or None
        unit_price = payload.unit_price_gnf
        override_reason = (getattr(payload, "price_override_reason", None) or "").strip()
        notes = (payload.notes or "").strip() or None
        price_audit_kind = None

        if payload.service_category == "hospitalization":
            if not payload.duration_value or payload.duration_unit not in ("days", "months"):
                raise HTTPException(status_code=400, detail="Durée d'hospitalisation requise")
            if not payload.specialty_code or payload.specialty_code == "pediatrics":
                raise HTTPException(status_code=400, detail="Sélectionnez une spécialité non pédiatrique")
            if payload.accommodation_type not in ("standard_bed", "private_cabin"):
                raise HTTPException(status_code=400, detail="Choisissez un lit standard ou une cabine privée")

        if catalog_code:
            cat = resolve_billing_catalog_item(catalog_code)
            if not cat:
                raise HTTPException(status_code=400, detail=f"Code catalogue inconnu: {catalog_code}")
            service_name = cat["label"]
            charge_type = cat["charge_type"]
            catalog_price = int(cat["price_gnf"])
            if override_reason:
                assert_permission(actor, Permission.BILLING_OVERRIDE)
                if unit_price is None:
                    raise HTTPException(
                        status_code=400,
                        detail="unit_price_gnf requis avec price_override_reason",
                    )
                notes = (
                    f"{notes + ' | ' if notes else ''}"
                    f"Prix négocié ({unit_price} GNF, catalogue {catalog_price}) — {override_reason}"
                )
                price_audit_kind = "price_override"
            else:
                # Ignore client-supplied price when catalog resolves.
                unit_price = catalog_price
        else:
            # Clinical DSRs may omit catalog/price (doctor/lab workflow).
            # Any client-supplied price on a non-catalog line requires free-text privilege.
            if unit_price is not None:
                assert_permission(actor, Permission.BILLING_FREE_TEXT)
                if not override_reason:
                    raise HTTPException(
                        status_code=400,
                        detail="price_override_reason requis pour demande hors catalogue",
                    )
                notes = (
                    f"{notes + ' | ' if notes else ''}"
                    f"Hors catalogue ({unit_price} GNF) — {override_reason}"
                )
                price_audit_kind = "free_text_charge"

        if not service_name:
            raise HTTPException(status_code=400, detail="service_name requis")

        quantity = payload.quantity
        if payload.service_category == "hospitalization":
            quantity = int(payload.duration_value) * (30 if payload.duration_unit == "months" else 1)
            from data.aasma_billing_catalog import SPECIALIZED_SPECIALTIES
            specialty = next((s for s in SPECIALIZED_SPECIALTIES if s["code"] == payload.specialty_code), None)
            if not specialty or specialty["code"] == "pediatrics":
                raise HTTPException(status_code=400, detail="Spécialité d'hospitalisation invalide")
            duration_label = "mois" if payload.duration_unit == "months" else "jour(s)"
            service_name = f"{service_name} — {specialty['label']} · {payload.duration_value} {duration_label}"

        row = models.ClinicServiceRequest(
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            admission_id=payload.admission_id,
            request_number="PENDING",
            service_category=payload.service_category,
            service_name=service_name,
            department=(payload.department or "").strip() or None,
            catalog_code=catalog_code,
            charge_type=charge_type,
            unit_price_gnf=unit_price,
            quantity=quantity,
            duration_value=payload.duration_value,
            duration_unit=payload.duration_unit,
            specialty_code=payload.specialty_code,
            accommodation_type=payload.accommodation_type,
            status=payload.status,
            notes=notes,
            created_by_user_id=actor.id,
            updated_by_user_id=actor.id,
        )
        db.add(row)
        db.flush()
        row.request_number = ReceptionHisService._service_request_number(clinic_id, row.id)
        db.commit()
        db.refresh(row)
        if price_audit_kind:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=payload.patient_id,
                action=price_audit_kind,
                resource_type="service_request",
                resource_id=row.id,
            )
        return row

    @staticmethod
    def get_service_request_by_number(
        db: Session,
        *,
        clinic_id: int,
        request_number: str,
    ) -> models.ClinicServiceRequest:
        number = (request_number or "").strip().upper()
        if not number:
            raise HTTPException(status_code=400, detail="N° de demande requis")
        row = (
            db.query(models.ClinicServiceRequest)
            .options(joinedload(models.ClinicServiceRequest.patient))
            .filter(
                models.ClinicServiceRequest.clinic_id == clinic_id,
                models.ClinicServiceRequest.request_number == number,
            )
            .first()
        )
        if not row and number.isdigit():
            row = (
                db.query(models.ClinicServiceRequest)
                .options(joinedload(models.ClinicServiceRequest.patient))
                .filter(
                    models.ClinicServiceRequest.clinic_id == clinic_id,
                    models.ClinicServiceRequest.id == int(number),
                )
                .first()
            )
        if not row:
            raise HTTPException(status_code=404, detail="Demande de service introuvable")
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
        from core.rbac import Permission, assert_permission
        from data.aasma_billing_catalog import resolve_billing_catalog_item

        data = payload.model_dump(exclude_unset=True)
        catalog_code = data.get("catalog_code", row.catalog_code)
        catalog_code = (catalog_code or "").strip() or None if catalog_code is not None else None
        override_reason = (data.get("price_override_reason") or "").strip()
        unit_price = data.get("unit_price_gnf", row.unit_price_gnf)
        price_touch = any(k in data for k in ("unit_price_gnf", "catalog_code", "price_override_reason"))
        price_audit_kind = None

        if price_touch:
            if catalog_code:
                cat = resolve_billing_catalog_item(catalog_code)
                if not cat:
                    raise HTTPException(status_code=400, detail=f"Code catalogue inconnu: {catalog_code}")
                data["service_name"] = cat["label"]
                data["charge_type"] = cat["charge_type"]
                data["catalog_code"] = catalog_code
                if override_reason:
                    assert_permission(actor, Permission.BILLING_OVERRIDE)
                    if unit_price is None:
                        raise HTTPException(
                            status_code=400,
                            detail="unit_price_gnf requis avec price_override_reason",
                        )
                    data["unit_price_gnf"] = int(unit_price)
                    price_audit_kind = "price_override"
                else:
                    data["unit_price_gnf"] = int(cat["price_gnf"])
            else:
                assert_permission(actor, Permission.BILLING_FREE_TEXT)
                if unit_price is None:
                    raise HTTPException(
                        status_code=400,
                        detail="unit_price_gnf requis pour demande hors catalogue",
                    )
                if not override_reason:
                    raise HTTPException(
                        status_code=400,
                        detail="price_override_reason requis pour demande hors catalogue",
                    )
                data["catalog_code"] = None
                data["unit_price_gnf"] = int(unit_price)
                price_audit_kind = "free_text_charge"

        resulting_category = data.get("service_category", row.service_category)
        if resulting_category == "hospitalization":
            duration_value = data.get("duration_value", row.duration_value)
            duration_unit = data.get("duration_unit", row.duration_unit)
            specialty_code = data.get("specialty_code", row.specialty_code)
            accommodation = data.get("accommodation_type", row.accommodation_type)
            if not duration_value or duration_unit not in ("days", "months"):
                raise HTTPException(status_code=400, detail="Durée d'hospitalisation requise")
            if specialty_code == "pediatrics" or not specialty_code:
                raise HTTPException(status_code=400, detail="Spécialité non pédiatrique requise")
            if accommodation not in ("standard_bed", "private_cabin"):
                raise HTTPException(status_code=400, detail="Type d'hébergement requis")
            data["quantity"] = int(duration_value) * (30 if duration_unit == "months" else 1)
            from data.aasma_billing_catalog import SPECIALIZED_SPECIALTIES
            specialty = next((s for s in SPECIALIZED_SPECIALTIES if s["code"] == specialty_code), None)
            if not specialty:
                raise HTTPException(status_code=400, detail="Spécialité d'hospitalisation invalide")
            base_label = "Hospitalisation — cabine privée" if accommodation == "private_cabin" else "Hospitalisation — lit standard"
            duration_label = "mois" if duration_unit == "months" else "jour(s)"
            data["service_name"] = f"{base_label} — {specialty['label']} · {duration_value} {duration_label}"

        data.pop("price_override_reason", None)
        for key, value in data.items():
            if key in ("service_name", "department", "notes") and isinstance(value, str):
                value = value.strip() or None
            setattr(row, key, value)
        row.updated_by_user_id = actor.id
        db.commit()
        db.refresh(row)
        if price_audit_kind:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=row.patient_id,
                action=price_audit_kind,
                resource_type="service_request",
                resource_id=row.id,
            )
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
