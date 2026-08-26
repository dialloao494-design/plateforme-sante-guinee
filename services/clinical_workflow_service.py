"""Clinical workflow orchestration — production state machine."""

from __future__ import annotations

from datetime import date, datetime, time
import uuid

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
from core.patient_number import format_patient_number
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
        # PostgreSQL enforces patients.patient_number NOT NULL. Allocate a unique
        # provisional value before flush, then replace it with the canonical
        # clinic-scoped dossier number as soon as the primary key exists.
        provisional_number = f"TMP-{clinic_id}-{uuid.uuid4().hex[:16].upper()}"
        patient = models.Patient(
            clinic_id=clinic_id,
            patient_number=provisional_number,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            age=payload.age,
            gender=payload.gender,
            phone=payload.phone,
            address=payload.address,
            date_of_birth=payload.date_of_birth,
            emergency_contact=payload.emergency_contact or payload.mother_name,
            mother_name=(payload.mother_name or "").strip() or None,
            profession=(payload.profession or "").strip() or None,
            quartier=(payload.quartier or "").strip() or None,
            visit_destination=(payload.visit_destination or "").strip() or None,
        )
        db.add(patient)
        db.flush()
        patient.patient_number = format_patient_number(clinic_id, patient.id)
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
        if not q:
            return []
        if q.isdigit():
            pid = int(q)
            patient = (
                db.query(models.Patient)
                .filter(
                    models.Patient.clinic_id == clinic_id,
                    models.Patient.id == pid,
                    models.Patient.is_archived.is_(False),
                )
                .first()
            )
            if patient:
                return [patient]
            if len(q) >= 8:
                pattern = f"%{q}%"
                return (
                    db.query(models.Patient)
                    .filter(
                        models.Patient.clinic_id == clinic_id,
                        models.Patient.is_archived.is_(False),
                        models.Patient.phone.ilike(pattern),
                    )
                    .order_by(models.Patient.last_name, models.Patient.first_name)
                    .limit(limit)
                    .all()
                )
            return []
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
            from services.nurse_assessment_service import NurseAssessmentService

            NurseAssessmentService.apply_to_consultation(
                db,
                clinic_id=clinic_id,
                patient_id=existing.patient_id,
                consultation=existing,
            )
            db.commit()
            db.refresh(existing)
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

        from services.nurse_assessment_service import NurseAssessmentService

        nurse_assessment = NurseAssessmentService.get_latest(
            db, clinic_id=clinic_id, patient_id=rdv.patient_id
        )
        resolved_complaint = chief_complaint
        if nurse_assessment and nurse_assessment.reason_for_consultation:
            resolved_complaint = nurse_assessment.reason_for_consultation.strip()

        consultation = models.ClinicalConsultation(
            clinic_id=clinic_id,
            appointment_id=appointment_id,
            patient_id=rdv.patient_id,
            doctor_id=doctor.id,
            status="in_progress",
            chief_complaint=resolved_complaint,
            started_at=datetime.utcnow(),
        )
        rdv.clinical_status = "in_consultation"
        db.add(consultation)
        db.flush()

        NurseAssessmentService.apply_to_consultation(
            db,
            clinic_id=clinic_id,
            patient_id=rdv.patient_id,
            consultation=consultation,
        )

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

        for field in (
            "chief_complaint",
            "history",
            "examination",
            "diagnosis",
            "treatment_plan",
            "medical_history",
            "surgical_history",
            "gyneco_history",
            "allergies",
            "current_treatments",
            "observations",
            "target_specialty_code",
            "target_specialty_other",
            "post_op_report",
            "discharge_summary_text",
            "discharge_authorization",
            "discharge_against_advice",
            "prescription_text",
            "discharge_form_json",
        ):
            val = getattr(payload, field, None)
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
    def doctor_waiting_queue(db: Session, *, clinic_id: int, doctor_id: int | None = None) -> list[dict]:
        """Patients ready for doctor review, including nurse-only handoffs."""
        today = date.today()
        start_today = datetime.combine(today, time.min)

        appt_query = (
            db.query(models.RendezVous)
            .options(joinedload(models.RendezVous.patient), joinedload(models.RendezVous.doctor))
            .filter(
                models.RendezVous.clinic_id == clinic_id,
                models.RendezVous.clinical_status.in_(("checked_in", "in_consultation")),
                models.RendezVous.status != "cancelled",
            )
        )
        if doctor_id is not None and doctor_id > 0:
            appt_query = appt_query.filter(models.RendezVous.doctor_id == doctor_id)
        appointments = appt_query.order_by(models.RendezVous.date.asc()).all()

        rows: list[dict] = []
        queued_patient_ids: set[int] = set()
        for rdv in appointments:
            queued_patient_ids.add(rdv.patient_id)
            patient_name = _patient_name(rdv.patient) if rdv.patient else "—"
            rows.append(
                {
                    "id": rdv.id,
                    "appointment_id": rdv.id,
                    "patient_id": rdv.patient_id,
                    "patient_name": patient_name,
                    "patient_number": rdv.patient.patient_number if rdv.patient else None,
                    "doctor_id": rdv.doctor_id,
                    "doctor_name": rdv.doctor.name if rdv.doctor else None,
                    "date": rdv.date.isoformat() if rdv.date else None,
                    "status": rdv.status,
                    "clinical_status": rdv.clinical_status,
                    "consultation_type": rdv.consultation_type,
                    "chief_complaint": None,
                    "source": "appointment",
                }
            )

        assessments = (
            db.query(models.NurseAssessment)
            .options(joinedload(models.NurseAssessment.patient))
            .filter(
                models.NurseAssessment.clinic_id == clinic_id,
                models.NurseAssessment.deleted_at.is_(None),
                models.NurseAssessment.recorded_at >= start_today,
            )
            .order_by(models.NurseAssessment.recorded_at.desc())
            .all()
        )
        seen_assessment_patients: set[int] = set()
        for assessment in assessments:
            if assessment.patient_id in queued_patient_ids or assessment.patient_id in seen_assessment_patients:
                continue
            seen_assessment_patients.add(assessment.patient_id)
            patient_name = _patient_name(assessment.patient) if assessment.patient else "—"
            rows.append(
                {
                    "id": f"assessment-{assessment.id}",
                    "assessment_id": assessment.id,
                    "patient_id": assessment.patient_id,
                    "patient_name": patient_name,
                    "patient_number": assessment.patient.patient_number if assessment.patient else None,
                    "doctor_id": None,
                    "doctor_name": None,
                    "date": assessment.recorded_at.isoformat() if assessment.recorded_at else None,
                    "status": "pending",
                    "clinical_status": "Évaluation infirmière",
                    "consultation_type": "physical",
                    "chief_complaint": assessment.reason_for_consultation,
                    "source": "nurse_assessment",
                }
            )
        return rows

    @staticmethod
    def open_consultation_for_patient(
        db: Session,
        *,
        clinic_id: int,
        doctor: models.Doctor,
        patient_id: int,
        chief_complaint: str | None = None,
        actor: User | None = None,
        client_ip: str | None = None,
    ) -> models.ClinicalConsultation:
        """Search-driven entry point: resume or start a consultation for a patient."""
        patient = (
            db.query(models.Patient)
            .filter(models.Patient.id == patient_id, models.Patient.clinic_id == clinic_id)
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient introuvable dans cette clinique")

        existing = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.patient_id == patient_id,
                models.ClinicalConsultation.doctor_id == doctor.id,
                models.ClinicalConsultation.status == "in_progress",
                models.ClinicalConsultation.deleted_at.is_(None),
            )
            .order_by(models.ClinicalConsultation.id.desc())
            .first()
        )
        if existing:
            from services.nurse_assessment_service import NurseAssessmentService

            NurseAssessmentService.apply_to_consultation(
                db,
                clinic_id=clinic_id,
                patient_id=existing.patient_id,
                consultation=existing,
            )
            db.commit()
            db.refresh(existing)
            return existing

        rdv = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.clinic_id == clinic_id,
                models.RendezVous.patient_id == patient_id,
                models.RendezVous.doctor_id == doctor.id,
                models.RendezVous.clinical_status.in_(("checked_in", "scheduled", "in_consultation")),
                models.RendezVous.status != "cancelled",
            )
            .order_by(models.RendezVous.date.desc())
            .first()
        )
        if rdv and rdv.clinical_status == "in_consultation":
            existing2 = (
                db.query(models.ClinicalConsultation)
                .filter(models.ClinicalConsultation.appointment_id == rdv.id)
                .first()
            )
            if existing2:
                return existing2
            rdv.clinical_status = "checked_in"
            db.commit()
        if not rdv:
            rdv = models.RendezVous(
                date=datetime.utcnow(),
                duration_minutes=30,
                status="confirmed",
                payment_status="pending",
                price=doctor.consultation_fee or 0,
                consultation_type="physical",
                doctor_id=doctor.id,
                patient_id=patient_id,
                clinic_id=clinic_id,
                clinical_status="checked_in",
            )
            db.add(rdv)
            db.commit()
            db.refresh(rdv)

        return ClinicalWorkflowService.start_consultation(
            db,
            clinic_id=clinic_id,
            appointment_id=rdv.id,
            doctor=doctor,
            chief_complaint=chief_complaint,
            actor=actor,
            client_ip=client_ip,
        )

    @staticmethod
    def patient_consultations(
        db: Session, *, clinic_id: int, patient_id: int, limit: int = 50
    ) -> list[dict]:
        rows = (
            db.query(models.ClinicalConsultation)
            .options(joinedload(models.ClinicalConsultation.doctor))
            .filter(
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.patient_id == patient_id,
                models.ClinicalConsultation.deleted_at.is_(None),
            )
            .order_by(models.ClinicalConsultation.created_at.desc())
            .limit(limit)
            .all()
        )
        out = []
        for c in rows:
            lab_names = [o.test_name for o in (c.lab_orders or [])]
            imaging_names = [o.modality for o in (c.imaging_orders or [])]
            services = []
            if lab_names:
                services.append("Labo: " + ", ".join(lab_names[:5]))
            if imaging_names:
                services.append("Imagerie: " + ", ".join(imaging_names[:5]))
            if c.prescriptions:
                services.append(f"Ordonnances: {len(c.prescriptions)}")
            out.append(
                {
                    "id": c.id,
                    "date": (c.started_at or c.created_at).isoformat()
                    if (c.started_at or c.created_at)
                    else None,
                    "status": c.status,
                    "doctor_name": c.doctor.name if c.doctor else None,
                    "chief_complaint": c.chief_complaint,
                    "diagnosis": c.diagnosis,
                    "treatment_plan": c.treatment_plan,
                    "requested_services": " | ".join(services) or "—",
                }
            )
        return out

    @staticmethod
    def doctor_dashboard_stats(db: Session, *, clinic_id: int, doctor_id: int) -> dict:
        today = date.today()
        start_today = datetime.combine(today, time.min)
        end_today = datetime.combine(today, time.max)

        appointment_waiting_query = db.query(models.RendezVous).filter(
            models.RendezVous.clinic_id == clinic_id,
            models.RendezVous.clinical_status.in_(("checked_in", "in_consultation")),
            models.RendezVous.status != "cancelled",
        )
        if doctor_id > 0:
            appointment_waiting_query = appointment_waiting_query.filter(
                models.RendezVous.doctor_id == doctor_id
            )
        appointment_waiting = appointment_waiting_query.count()
        appointment_patient_query = db.query(models.RendezVous.patient_id).filter(
            models.RendezVous.clinic_id == clinic_id,
            models.RendezVous.clinical_status.in_(("checked_in", "in_consultation")),
            models.RendezVous.status != "cancelled",
        )
        if doctor_id > 0:
            appointment_patient_query = appointment_patient_query.filter(
                models.RendezVous.doctor_id == doctor_id
            )
        appointment_patient_ids = {
            row[0]
            for row in appointment_patient_query.all()
        }
        nurse_waiting = (
            db.query(models.NurseAssessment.patient_id)
            .filter(
                models.NurseAssessment.clinic_id == clinic_id,
                models.NurseAssessment.deleted_at.is_(None),
                models.NurseAssessment.recorded_at >= start_today,
                ~models.NurseAssessment.patient_id.in_(appointment_patient_ids or {-1}),
            )
            .distinct()
            .count()
        )
        consultations_today = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.doctor_id == doctor_id,
                models.ClinicalConsultation.started_at >= start_today,
                models.ClinicalConsultation.started_at <= end_today,
                models.ClinicalConsultation.deleted_at.is_(None),
            )
            .count()
        )
        completed_today = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.doctor_id == doctor_id,
                models.ClinicalConsultation.status == "completed",
                models.ClinicalConsultation.completed_at >= start_today,
                models.ClinicalConsultation.completed_at <= end_today,
                models.ClinicalConsultation.deleted_at.is_(None),
            )
            .count()
        )
        hospitalized = (
            db.query(models.Admission)
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.admission_type == "hospitalization",
                models.Admission.status.in_(["admitted", "in_care", "pending"]),
            )
            .count()
        )
        lab_pending = (
            db.query(models.LabOrder)
            .join(
                models.ClinicalConsultation,
                models.LabOrder.consultation_id == models.ClinicalConsultation.id,
            )
            .filter(
                models.LabOrder.clinic_id == clinic_id,
                models.ClinicalConsultation.doctor_id == doctor_id,
                models.LabOrder.status.in_(["ordered", "sample_collected", "in_analysis"]),
            )
            .count()
        )
        imaging_pending = (
            db.query(models.ImagingOrder)
            .join(
                models.ClinicalConsultation,
                models.ImagingOrder.consultation_id == models.ClinicalConsultation.id,
            )
            .filter(
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.doctor_id == doctor_id,
                models.ImagingOrder.status.in_(["ordered", "scheduled", "in_progress"]),
            )
            .count()
        )
        return {
            "patients_waiting": appointment_waiting + nurse_waiting,
            "consultations_today": consultations_today,
            "hospitalized_patients": hospitalized,
            "lab_pending": lab_pending,
            "imaging_pending": imaging_pending,
            "completed_consultations": completed_today,
        }

    @staticmethod
    def doctor_dashboard_queue(
        db: Session, *, clinic_id: int, doctor_id: int, bucket: str
    ) -> list[dict]:
        today = date.today()
        start_today = datetime.combine(today, time.min)
        end_today = datetime.combine(today, time.max)

        def pname(patient) -> str:
            if not patient:
                return "—"
            return f"{patient.last_name} {patient.first_name}".strip()

        if bucket == "patients_waiting":
            return ClinicalWorkflowService.doctor_waiting_queue(
                db, clinic_id=clinic_id, doctor_id=doctor_id
            )

        if bucket in ("consultations_today", "completed_consultations"):
            query = (
                db.query(models.ClinicalConsultation)
                .options(joinedload(models.ClinicalConsultation.patient))
                .filter(
                    models.ClinicalConsultation.clinic_id == clinic_id,
                    models.ClinicalConsultation.doctor_id == doctor_id,
                    models.ClinicalConsultation.deleted_at.is_(None),
                )
            )
            if bucket == "completed_consultations":
                query = query.filter(
                    models.ClinicalConsultation.status == "completed",
                    models.ClinicalConsultation.completed_at >= start_today,
                    models.ClinicalConsultation.completed_at <= end_today,
                )
            else:
                query = query.filter(
                    models.ClinicalConsultation.started_at >= start_today,
                    models.ClinicalConsultation.started_at <= end_today,
                )
            rows = query.order_by(models.ClinicalConsultation.id.desc()).all()
            return [
                {
                    "consultation_id": c.id,
                    "patient_id": c.patient_id,
                    "patient_name": pname(c.patient),
                    "status": c.status,
                    "diagnosis": c.diagnosis,
                    "date": (c.started_at or c.created_at).isoformat()
                    if (c.started_at or c.created_at)
                    else None,
                }
                for c in rows
            ]

        if bucket == "hospitalized_patients":
            rows = (
                db.query(models.Admission)
                .options(joinedload(models.Admission.patient))
                .filter(
                    models.Admission.clinic_id == clinic_id,
                    models.Admission.admission_type == "hospitalization",
                    models.Admission.status.in_(["admitted", "in_care", "pending"]),
                )
                .order_by(models.Admission.admitted_at.desc())
                .all()
            )
            return [
                {
                    "admission_id": a.id,
                    "patient_id": a.patient_id,
                    "patient_name": pname(a.patient),
                    "status": a.status,
                    "admitted_at": a.admitted_at.isoformat() if a.admitted_at else None,
                }
                for a in rows
            ]

        if bucket == "lab_pending":
            rows = (
                db.query(models.LabOrder)
                .join(
                    models.ClinicalConsultation,
                    models.LabOrder.consultation_id == models.ClinicalConsultation.id,
                )
                .options(joinedload(models.LabOrder.patient))
                .filter(
                    models.LabOrder.clinic_id == clinic_id,
                    models.ClinicalConsultation.doctor_id == doctor_id,
                    models.LabOrder.status.in_(["ordered", "sample_collected", "in_analysis"]),
                )
                .order_by(models.LabOrder.id.desc())
                .all()
            )
            return [
                {
                    "order_id": o.id,
                    "patient_id": o.patient_id,
                    "patient_name": pname(o.patient),
                    "test_name": o.test_name,
                    "status": o.status,
                }
                for o in rows
            ]

        if bucket == "imaging_pending":
            rows = (
                db.query(models.ImagingOrder)
                .join(
                    models.ClinicalConsultation,
                    models.ImagingOrder.consultation_id == models.ClinicalConsultation.id,
                )
                .options(joinedload(models.ImagingOrder.patient))
                .filter(
                    models.ClinicalConsultation.clinic_id == clinic_id,
                    models.ClinicalConsultation.doctor_id == doctor_id,
                    models.ImagingOrder.status.in_(["ordered", "scheduled", "in_progress"]),
                )
                .order_by(models.ImagingOrder.id.desc())
                .all()
            )
            return [
                {
                    "order_id": o.id,
                    "patient_id": o.patient_id,
                    "patient_name": pname(o.patient),
                    "modality": o.modality,
                    "body_part": getattr(o, "body_part", None),
                    "status": o.status,
                }
                for o in rows
            ]

        return []

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
        if payload.status is not None and payload.status not in allowed:
            raise HTTPException(status_code=400, detail=f"Invalid status. Allowed: {sorted(allowed)}")
        if payload.status is None and payload.clinical_notes is None:
            raise HTTPException(status_code=400, detail="Fournir status et/ou clinical_notes")

        order = (
            db.query(models.LabOrder)
            .filter(models.LabOrder.id == order_id, models.LabOrder.clinic_id == clinic_id)
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Lab order not found")
        if payload.status is not None:
            order.status = payload.status
        if payload.clinical_notes is not None:
            order.clinical_notes = payload.clinical_notes
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
