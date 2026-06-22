"""Clinical workflow orchestration — production state machine."""

from __future__ import annotations

from datetime import datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

import models
from models.user import User
from schemas.clinical import (
    ClinicalAppointmentCreate,
    ConsultationUpdate,
    LabOrderCreate,
    LabOrderStatusUpdate,
    LabResultCreate,
    PatientIntakeCreate,
    PharmacyStatusUpdate,
    PrescriptionCreate,
    PrescriptionItemCreate,
)
from services.clinic_billing_service import ClinicBillingService
from services.cis_audit import log_cis
from services.rendezvous_service import RendezVousService, _cmp_dt
from schemas import rendezvous as rendezvous_schemas


def _patient_name(patient: models.Patient) -> str:
    return f"{patient.first_name} {patient.last_name}".strip()


class ClinicalWorkflowService:
    @staticmethod
    def _validate_clinical_appointment(
        rdv: rendezvous_schemas.RendezVousCreate,
        patient: models.Patient,
        doctor: models.Doctor,
        db: Session,
    ) -> None:
        """In-clinic booking: overlap and past checks only (no public availability grid)."""
        from datetime import datetime as dt

        now = dt.now(rdv.date.tzinfo) if rdv.date.tzinfo else dt.now()
        if _cmp_dt(rdv.date) < _cmp_dt(now):
            raise HTTPException(status_code=400, detail="Cannot book appointments in the past")

        overlap = RendezVousService.check_overlap_with_duration(
            doctor_id=doctor.id,
            start_time=rdv.date,
            duration_minutes=rdv.duration_minutes,
            db=db,
        )
        if overlap:
            raise HTTPException(status_code=409, detail="Ce créneau est déjà réservé")

    @staticmethod
    def register_patient(
        db: Session,
        *,
        clinic_id: int,
        payload: PatientIntakeCreate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.Patient:
        if payload.phone:
            digits = "".join(c for c in payload.phone if c.isdigit())[-9:]
            existing = (
                db.query(models.Patient)
                .filter(
                    models.Patient.clinic_id == clinic_id,
                    models.Patient.phone.isnot(None),
                    models.Patient.is_archived.is_(False),
                )
                .all()
            )
            for p in existing:
                p_digits = "".join(c for c in (p.phone or "") if c.isdigit())[-9:]
                if p_digits and p_digits == digits:
                    raise HTTPException(
                        status_code=409,
                        detail="Un patient avec ce numéro existe déjà dans cette clinique",
                    )
        patient = models.Patient(
            clinic_id=clinic_id,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            age=payload.age,
            gender=payload.gender,
            phone=payload.phone,
            address=payload.address,
            date_of_birth=payload.date_of_birth,
            emergency_contact=payload.emergency_contact or payload.mother_name,
            mother_name=payload.mother_name.strip(),
            profession=(payload.profession or "").strip() or None,
            quartier=(payload.quartier or "").strip() or None,
            visit_destination=payload.visit_destination.strip(),
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        from services.medical_history_service import ensure_medical_record

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
        db: Session, *, clinic_id: int, query: str, limit: int = 20
    ) -> list[models.Patient]:
        q = query.strip()
        if len(q) < 2:
            return []
        pattern = f"%{q}%"
        return (
            db.query(models.Patient)
            .filter(
                models.Patient.clinic_id == clinic_id,
                models.Patient.is_archived.is_(False),
                (
                    models.Patient.first_name.ilike(pattern)
                    | models.Patient.last_name.ilike(pattern)
                    | models.Patient.phone.ilike(pattern)
                ),
            )
            .order_by(models.Patient.last_name, models.Patient.first_name)
            .limit(limit)
            .all()
        )

    @staticmethod
    def create_appointment(
        db: Session,
        *,
        clinic_id: int,
        payload: ClinicalAppointmentCreate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.RendezVous:
        patient = db.query(models.Patient).filter(models.Patient.id == payload.patient_id).first()
        doctor = db.query(models.Doctor).filter(models.Doctor.id == payload.doctor_id).first()
        if not patient or not doctor:
            raise HTTPException(status_code=404, detail="Patient or doctor not found")
        if patient.clinic_id is None:
            raise HTTPException(
                status_code=403,
                detail="Patient is not registered at this clinic",
            )
        if patient.clinic_id != clinic_id:
            raise HTTPException(
                status_code=403,
                detail="Patient belongs to another clinic",
            )
        if doctor.clinic_id and doctor.clinic_id != clinic_id:
            raise HTTPException(status_code=400, detail="Doctor not in this clinic")

        rdv_schema = rendezvous_schemas.RendezVousCreate(
            doctor_id=payload.doctor_id,
            date=payload.date,
            duration_minutes=payload.duration_minutes,
            consultation_type=payload.consultation_type,
        )
        ClinicalWorkflowService._validate_clinical_appointment(rdv_schema, patient, doctor, db)
        fee = doctor.consultation_fee or 150_000
        rdv = models.RendezVous(
            date=payload.date,
            duration_minutes=payload.duration_minutes,
            status="confirmed",
            payment_status="pending",
            price=fee,
            consultation_type=payload.consultation_type,
            doctor_id=payload.doctor_id,
            patient_id=payload.patient_id,
            clinic_id=clinic_id,
            clinical_status="scheduled",
        )
        db.add(rdv)
        db.commit()
        db.refresh(rdv)
        ClinicBillingService.create_consultation_charge(
            db,
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            appointment_id=rdv.id,
            amount_gnf=fee,
            description=f"Consultation — Dr. {doctor.name}",
        )
        if actor:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=payload.patient_id,
                action="create",
                resource_type="appointment",
                resource_id=rdv.id,
                client_ip=client_ip,
            )
        from services.reminder_service import ReminderService

        ReminderService.schedule_for_appointment(db, rdv)
        return rdv

    @staticmethod
    def check_in_appointment(
        db: Session,
        *,
        appointment_id: int,
        clinic_id: int,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.RendezVous:
        rdv = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.id == appointment_id,
                models.RendezVous.clinic_id == clinic_id,
            )
            .first()
        )
        if not rdv:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if rdv.clinical_status not in ("scheduled",):
            raise HTTPException(status_code=400, detail=f"Cannot check-in from status {rdv.clinical_status}")
        rdv.clinical_status = "checked_in"
        rdv.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(rdv)
        if actor:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=rdv.patient_id,
                action="update",
                resource_type="appointment_check_in",
                resource_id=rdv.id,
                client_ip=client_ip,
            )
        return rdv

    @staticmethod
    def reception_queue(db: Session, *, clinic_id: int) -> list[models.RendezVous]:
        return (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.clinic_id == clinic_id,
                models.RendezVous.clinical_status.in_(("scheduled", "checked_in")),
                models.RendezVous.status != "cancelled",
            )
            .order_by(models.RendezVous.date.asc())
            .all()
        )

    @staticmethod
    def start_consultation(
        db: Session,
        *,
        clinic_id: int,
        appointment_id: int,
        doctor: models.Doctor,
        chief_complaint: str | None = None,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.ClinicalConsultation:
        rdv = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.id == appointment_id,
                models.RendezVous.clinic_id == clinic_id,
                models.RendezVous.doctor_id == doctor.id,
            )
            .first()
        )
        if not rdv:
            raise HTTPException(status_code=404, detail="Appointment not found")

        existing = (
            db.query(models.ClinicalConsultation)
            .filter(models.ClinicalConsultation.appointment_id == appointment_id)
            .first()
        )
        if existing:
            if actor:
                log_cis(
                    db,
                    actor=actor,
                    clinic_id=clinic_id,
                    patient_id=existing.patient_id,
                    action="read",
                    resource_type="consultation",
                    resource_id=existing.id,
                    client_ip=client_ip,
                )
            return existing

        if rdv.clinical_status not in ("checked_in", "scheduled"):
            raise HTTPException(status_code=400, detail="Appointment not ready for consultation")

        consultation = models.ClinicalConsultation(
            clinic_id=clinic_id,
            appointment_id=appointment_id,
            patient_id=rdv.patient_id,
            doctor_id=doctor.id,
            status="in_progress",
            chief_complaint=chief_complaint,
            started_at=datetime.utcnow(),
        )
        rdv.clinical_status = "in_consultation"
        db.add(consultation)
        db.commit()
        db.refresh(consultation)
        from services.visit_service import VisitService

        VisitService.ensure_for_consultation(db, consultation)
        if actor:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=consultation.patient_id,
                action="create",
                resource_type="consultation",
                resource_id=consultation.id,
                client_ip=client_ip,
            )
        return consultation

    @staticmethod
    def update_consultation(
        db: Session,
        *,
        consultation_id: int,
        clinic_id: int,
        doctor_id: int,
        payload: ConsultationUpdate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.ClinicalConsultation:
        consultation = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.id == consultation_id,
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.doctor_id == doctor_id,
            )
            .first()
        )
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        for field in ("chief_complaint", "history", "examination", "diagnosis", "treatment_plan"):
            val = getattr(payload, field)
            if val is not None:
                setattr(consultation, field, val)

        if payload.status == "completed":
            consultation.status = "completed"
            consultation.completed_at = datetime.utcnow()
            rdv = consultation.appointment
            if rdv:
                rdv.clinical_status = "completed"
                rdv.status = "completed"
            from services.medical_history_service import MedicalHistoryService

            MedicalHistoryService.snapshot_consultation_to_dossier(
                db, consultation, actor=actor
            )

        consultation.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(consultation)
        if actor:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=consultation.patient_id,
                action="update",
                resource_type="consultation",
                resource_id=consultation.id,
                client_ip=client_ip,
            )
        return consultation

    @staticmethod
    def doctor_queue(db: Session, *, clinic_id: int, doctor_id: int) -> list[models.RendezVous]:
        return (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.clinic_id == clinic_id,
                models.RendezVous.doctor_id == doctor_id,
                models.RendezVous.clinical_status.in_(("checked_in", "in_consultation")),
                models.RendezVous.status != "cancelled",
            )
            .order_by(models.RendezVous.date.asc())
            .all()
        )

    @staticmethod
    def create_lab_order(
        db: Session,
        *,
        clinic_id: int,
        consultation_id: int,
        doctor: models.Doctor,
        user: User,
        payload: LabOrderCreate,
        client_ip: str | None = None,
    ) -> models.LabOrder:
        consultation = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.id == consultation_id,
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.doctor_id == doctor.id,
            )
            .first()
        )
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        order = models.LabOrder(
            clinic_id=clinic_id,
            consultation_id=consultation_id,
            patient_id=consultation.patient_id,
            ordered_by_user_id=user.id,
            doctor_id=doctor.id,
            test_code=payload.test_code.strip(),
            test_name=payload.test_name.strip(),
            priority=payload.priority,
            clinical_notes=payload.clinical_notes,
            status="ordered",
        )
        db.add(order)
        db.commit()
        db.refresh(order)
        ClinicBillingService.create_lab_charge(
            db,
            clinic_id=clinic_id,
            patient_id=consultation.patient_id,
            lab_order_id=order.id,
            test_name=order.test_name,
        )
        log_cis(
            db,
            actor=user,
            clinic_id=clinic_id,
            patient_id=consultation.patient_id,
            action="create",
            resource_type="lab_order",
            resource_id=order.id,
            client_ip=client_ip,
        )
        return order

    @staticmethod
    def lab_queue(db: Session, *, clinic_id: int) -> list[models.LabOrder]:
        return (
            db.query(models.LabOrder)
            .options(joinedload(models.LabOrder.patient))
            .filter(
                models.LabOrder.clinic_id == clinic_id,
                models.LabOrder.status.in_(("ordered", "sample_collected", "in_analysis")),
            )
            .order_by(models.LabOrder.created_at.asc())
            .all()
        )

    @staticmethod
    def update_lab_order_status(
        db: Session,
        *,
        order_id: int,
        clinic_id: int,
        payload: LabOrderStatusUpdate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.LabOrder:
        allowed = {"ordered", "sample_collected", "in_analysis", "completed", "cancelled"}
        if payload.status not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(allowed)}")

        order = (
            db.query(models.LabOrder)
            .filter(models.LabOrder.id == order_id, models.LabOrder.clinic_id == clinic_id)
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Lab order not found")
        order.status = payload.status
        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
        if actor:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=order.patient_id,
                action="update",
                resource_type="lab_order",
                resource_id=order.id,
                client_ip=client_ip,
            )
        return order

    @staticmethod
    def record_lab_result(
        db: Session,
        *,
        order_id: int,
        clinic_id: int,
        user: User,
        payload: LabResultCreate,
        client_ip: str | None = None,
    ) -> models.LabResult:
        order = (
            db.query(models.LabOrder)
            .filter(models.LabOrder.id == order_id, models.LabOrder.clinic_id == clinic_id)
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Lab order not found")

        existing = (
            db.query(models.LabResult).filter(models.LabResult.lab_order_id == order_id).first()
        )
        if existing:
            existing.result_summary = payload.result_summary
            existing.result_data = payload.result_data
            existing.reference_range = payload.reference_range
            existing.interpretation = payload.interpretation
            existing.recorded_by_user_id = user.id
            existing.updated_at = datetime.utcnow()
            result = existing
        else:
            result = models.LabResult(
                lab_order_id=order_id,
                recorded_by_user_id=user.id,
                result_summary=payload.result_summary,
                result_data=payload.result_data,
                reference_range=payload.reference_range,
                interpretation=payload.interpretation,
                status="draft",
            )
            db.add(result)

        order.status = "in_analysis"
        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(result)
        log_cis(
            db,
            actor=user,
            clinic_id=clinic_id,
            patient_id=order.patient_id,
            action="create",
            resource_type="lab_result",
            resource_id=result.id,
            client_ip=client_ip,
        )
        return result

    @staticmethod
    def validate_lab_result(
        db: Session,
        *,
        result_id: int,
        clinic_id: int,
        user: User,
        client_ip: str | None = None,
    ) -> models.LabResult:
        result = (
            db.query(models.LabResult)
            .join(models.LabOrder)
            .filter(models.LabResult.id == result_id, models.LabOrder.clinic_id == clinic_id)
            .first()
        )
        if not result:
            raise HTTPException(status_code=404, detail="Lab result not found")
        result.status = "validated"
        result.validated_at = datetime.utcnow()
        result.validated_by_user_id = user.id
        result.lab_order.status = "completed"
        db.commit()
        db.refresh(result)
        ClinicalWorkflowService.attach_lab_result_document(
            db, order=result.lab_order, result=result, user=user
        )
        log_cis(
            db,
            actor=user,
            clinic_id=clinic_id,
            patient_id=result.lab_order.patient_id,
            action="update",
            resource_type="lab_result_validate",
            resource_id=result.id,
            client_ip=client_ip,
        )
        return result

    @staticmethod
    def attach_lab_result_document(
        db: Session,
        *,
        order: models.LabOrder,
        result: models.LabResult,
        user: User,
    ) -> None:
        """Persist validated lab result as a patient document (text archive)."""
        from services.secure_attachment_storage import SecureAttachmentStorage

        body = (
            f"Examen: {order.test_name} ({order.test_code})\n"
            f"Résultat: {result.result_summary or '—'}\n"
            f"Référence: {result.reference_range or '—'}\n"
            f"Interprétation: {result.interpretation or '—'}\n"
            f"Validé le: {result.validated_at or datetime.utcnow()}\n"
        ).encode("utf-8")
        stored = SecureAttachmentStorage.store(
            body, original_filename=f"lab_result_{order.id}.txt", extension=".txt"
        )
        doc = models.PatientDocument(
            patient_id=order.patient_id,
            uploaded_by=user.id,
            type_document="lab_result",
            file_path=stored.storage_key,
        )
        db.add(doc)
        db.commit()

    @staticmethod
    def create_prescription(
        db: Session,
        *,
        clinic_id: int,
        consultation_id: int,
        doctor: models.Doctor,
        payload: PrescriptionCreate,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.Prescription:
        if not payload.items:
            raise HTTPException(status_code=400, detail="Prescription requires at least one item")

        consultation = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.id == consultation_id,
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.doctor_id == doctor.id,
            )
            .first()
        )
        if not consultation:
            raise HTTPException(status_code=404, detail="Consultation not found")

        rx = models.Prescription(
            clinic_id=clinic_id,
            consultation_id=consultation_id,
            patient_id=consultation.patient_id,
            prescriber_doctor_id=doctor.id,
            status="active",
            notes=payload.notes,
        )
        db.add(rx)
        db.flush()

        for item in payload.items:
            db.add(
                models.PrescriptionItem(
                    prescription_id=rx.id,
                    medication_name=item.medication_name,
                    dosage=item.dosage,
                    route=item.route,
                    frequency=item.frequency,
                    duration_days=item.duration_days,
                    quantity=item.quantity,
                    instructions=item.instructions,
                )
            )

        pharmacy_order = models.PharmacyOrder(
            clinic_id=clinic_id,
            prescription_id=rx.id,
            patient_id=consultation.patient_id,
            status="pending",
        )
        db.add(pharmacy_order)
        db.flush()
        meds = ", ".join(i.medication_name for i in payload.items)
        amount = ClinicBillingService.pharmacy_amount_from_items(payload.items)
        ClinicBillingService.create_pharmacy_charge(
            db,
            clinic_id=clinic_id,
            patient_id=consultation.patient_id,
            pharmacy_order_id=pharmacy_order.id,
            medications=meds,
            amount_gnf=amount,
        )
        db.commit()
        db.refresh(rx)
        if actor:
            log_cis(
                db,
                actor=actor,
                clinic_id=clinic_id,
                patient_id=consultation.patient_id,
                action="create",
                resource_type="prescription",
                resource_id=rx.id,
                client_ip=client_ip,
            )
        return rx

    @staticmethod
    def list_pharmacy_orders(
        db: Session, *, clinic_id: int, scope: str = "active"
    ) -> list[models.PharmacyOrder]:
        q = db.query(models.PharmacyOrder).filter(models.PharmacyOrder.clinic_id == clinic_id)
        if scope == "active":
            q = q.filter(
                models.PharmacyOrder.status.in_(
                    ("pending", "preparing", "ready", "partially_dispensed")
                )
            )
        elif scope == "dispensed_today":
            from datetime import datetime, timedelta

            start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            end = start + timedelta(days=1)
            q = q.filter(
                models.PharmacyOrder.status == "dispensed",
                models.PharmacyOrder.dispensed_at >= start,
                models.PharmacyOrder.dispensed_at < end,
            )
        elif scope == "history":
            q = q.filter(
                models.PharmacyOrder.status.in_(
                    ("dispensed", "partially_dispensed", "cancelled")
                )
            )
        elif scope != "all":
            raise HTTPException(status_code=400, detail=f"Unknown scope: {scope}")
        if scope == "active":
            return q.order_by(models.PharmacyOrder.created_at.asc()).all()
        return q.order_by(models.PharmacyOrder.created_at.desc()).all()

    @staticmethod
    def pharmacy_queue(db: Session, *, clinic_id: int) -> list[models.PharmacyOrder]:
        return ClinicalWorkflowService.list_pharmacy_orders(db, clinic_id=clinic_id, scope="active")

    @staticmethod
    def update_pharmacy_order(
        db: Session,
        *,
        order_id: int,
        clinic_id: int,
        user: User,
        payload: PharmacyStatusUpdate,
        client_ip: str | None = None,
    ) -> models.PharmacyOrder:
        allowed = {"pending", "preparing", "ready", "partially_dispensed", "dispensed", "cancelled"}
        if payload.status not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(allowed)}")

        order = (
            db.query(models.PharmacyOrder)
            .filter(models.PharmacyOrder.id == order_id, models.PharmacyOrder.clinic_id == clinic_id)
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Pharmacy order not found")

        order.status = payload.status
        order.notes = payload.notes or order.notes
        order.prepared_by_user_id = user.id
        if payload.status == "dispensed":
            order.dispensed_at = datetime.utcnow()
            order.prescription.status = "dispensed"
            meds = ", ".join(
                i.medication_name for i in (order.prescription.items or [])
            ) if order.prescription else ""
            from services.pharmacy_inventory_service import PharmacyInventoryService

            PharmacyInventoryService.deduct_for_prescription(
                db, clinic_id=clinic_id, medications_text=meds
            )

        order.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(order)
        log_cis(
            db,
            actor=user,
            clinic_id=clinic_id,
            patient_id=order.patient_id,
            action="update",
            resource_type="pharmacy_order",
            resource_id=order.id,
            client_ip=client_ip,
        )
        return order

    @staticmethod
    def patient_journey(
        db: Session, *, clinic_id: int, patient_id: int
    ) -> dict:
        """Full workflow trace for dashboards."""
        appointments = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.clinic_id == clinic_id,
                models.RendezVous.patient_id == patient_id,
            )
            .order_by(models.RendezVous.created_at.desc())
            .all()
        )
        consultations = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.patient_id == patient_id,
            )
            .all()
        )
        immunizations = (
            db.query(models.ImmunizationRecord)
            .filter(
                models.ImmunizationRecord.clinic_id == clinic_id,
                models.ImmunizationRecord.patient_id == patient_id,
                models.ImmunizationRecord.deleted_at.is_(None),
            )
            .order_by(models.ImmunizationRecord.administered_at.desc())
            .all()
        )
        return {
            "patient_id": patient_id,
            "appointments": [
                {"id": a.id, "clinical_status": a.clinical_status, "date": a.date.isoformat()}
                for a in appointments
            ],
            "consultations": [{"id": c.id, "status": c.status} for c in consultations],
            "immunizations": [
                {
                    "id": r.id,
                    "vaccine_name": r.vaccine_name,
                    "dose_label": r.dose_label,
                    "administered_at": r.administered_at.isoformat(),
                    "vaccinator_name": r.vaccinator_name,
                }
                for r in immunizations
            ],
        }
