"""Nurse triage / assessment service."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

import models
import schemas.medical_history as mh_schemas
import schemas.nurse_assessment as na_schemas
from core.tenant import assert_patient_in_clinic
from models.user import User
from services.clinical_audit_service import ClinicalAuditService
from services.medical_history_service import MedicalHistoryService
from services.patient_record_access import PatientRecordAccessPolicy


def _patient_age(patient: models.Patient) -> Optional[int]:
    if patient.age is not None:
        return patient.age
    if patient.date_of_birth:
        return (date.today() - patient.date_of_birth).days // 365
    return None


def _combine_history(assessment: models.NurseAssessment) -> Optional[str]:
    sections: list[str] = []
    mapping = [
        ("Histoire de la maladie", assessment.history_of_present_illness),
        ("Antécédents médicaux", assessment.medical_history),
        ("Antécédents chirurgicaux", assessment.surgical_history),
        ("Antécédents gynéco-obstétricaux", assessment.gynecological_history),
        ("Allergies", assessment.allergies),
        ("Traitements en cours", assessment.current_treatments),
        ("Signes vitaux hospitalisés - soins quotidiens", assessment.hospitalized_daily_vitals),
        ("Prescription", assessment.prescription),
        ("Notes infirmières", assessment.nurse_notes),
    ]
    for label, value in mapping:
        text = (value or "").strip()
        if text:
            sections.append(f"{label}:\n{text}")
    return "\n\n".join(sections) if sections else None


def _serialize_assessment(row: models.NurseAssessment) -> na_schemas.NurseAssessmentResponse:
    patient = row.patient
    return na_schemas.NurseAssessmentResponse(
        id=row.id,
        clinic_id=row.clinic_id,
        patient_id=row.patient_id,
        admission_id=row.admission_id,
        appointment_id=row.appointment_id,
        consultation_id=row.consultation_id,
        nurse_user_id=row.nurse_user_id,
        nurse_name=row.nurse_name,
        temperature_c=row.temperature_c,
        bp_systolic=row.bp_systolic,
        bp_diastolic=row.bp_diastolic,
        heart_rate=row.heart_rate,
        respiratory_rate=row.respiratory_rate,
        height_cm=row.height_cm,
        weight_kg=row.weight_kg,
        bmi=row.bmi,
        vitals_observations=row.vitals_observations,
        reason_for_consultation=row.reason_for_consultation,
        history_of_present_illness=row.history_of_present_illness,
        medical_history=row.medical_history,
        surgical_history=row.surgical_history,
        gynecological_history=row.gynecological_history,
        allergies=row.allergies,
        current_treatments=row.current_treatments,
        hospitalized_daily_vitals=row.hospitalized_daily_vitals,
        prescription=row.prescription,
        nurse_notes=row.nurse_notes,
        recorded_at=row.recorded_at,
        updated_at=row.updated_at,
        patient_number=patient.patient_number if patient else None,
        patient_name=f"{patient.last_name} {patient.first_name}".strip() if patient else None,
        patient_age=_patient_age(patient) if patient else None,
        patient_gender=patient.gender if patient else None,
    )


class NurseAssessmentService:
    @staticmethod
    def _today_start() -> datetime:
        today = date.today()
        return datetime.combine(today, time.min)

    @staticmethod
    def get_latest(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        admission_id: Optional[int] = None,
    ) -> Optional[models.NurseAssessment]:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        q = (
            db.query(models.NurseAssessment)
            .options(joinedload(models.NurseAssessment.patient))
            .filter(
                models.NurseAssessment.clinic_id == clinic_id,
                models.NurseAssessment.patient_id == patient_id,
                models.NurseAssessment.deleted_at.is_(None),
            )
        )
        if admission_id:
            q = q.filter(models.NurseAssessment.admission_id == admission_id)
        return q.order_by(models.NurseAssessment.recorded_at.desc()).first()

    @staticmethod
    def _resolve_admission_id(
        db: Session, *, clinic_id: int, patient_id: int, admission_id: Optional[int]
    ) -> Optional[int]:
        if admission_id:
            return admission_id
        admission = (
            db.query(models.Admission)
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.patient_id == patient_id,
                models.Admission.admitted_at >= NurseAssessmentService._today_start(),
            )
            .order_by(models.Admission.admitted_at.desc())
            .first()
        )
        return admission.id if admission else None

    @staticmethod
    def save_assessment(
        db: Session,
        *,
        clinic_id: int,
        payload: na_schemas.NurseAssessmentCreate,
        actor: User,
        client_ip: str | None = None,
    ) -> models.NurseAssessment:
        PatientRecordAccessPolicy.assert_can_write_clinical(db, actor, payload.patient_id)
        assert_patient_in_clinic(db, patient_id=payload.patient_id, clinic_id=clinic_id)

        admission_id = NurseAssessmentService._resolve_admission_id(
            db,
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            admission_id=payload.admission_id,
        )

        existing = NurseAssessmentService.get_latest(
            db,
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            admission_id=admission_id,
        )

        bmi = na_schemas.calc_bmi(payload.weight_kg, payload.height_cm)
        nurse_name = getattr(actor, "full_name", None) or actor.email
        now = datetime.utcnow()
        data = payload.model_dump(exclude={"admission_id", "appointment_id", "consultation_id"})
        data["bmi"] = bmi
        data["admission_id"] = admission_id

        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            existing.nurse_user_id = actor.id
            existing.nurse_name = nurse_name
            existing.updated_at = now
            row = existing
        else:
            row = models.NurseAssessment(
                clinic_id=clinic_id,
                nurse_user_id=actor.id,
                nurse_name=nurse_name,
                recorded_at=now,
                updated_at=now,
                **data,
            )
            db.add(row)

        db.flush()

        vitals_notes = payload.vitals_observations
        if bmi is not None:
            bmi_note = f"IMC: {bmi}"
            vitals_notes = f"{vitals_notes}\n{bmi_note}".strip() if vitals_notes else bmi_note

        consultation_id = payload.consultation_id
        if not consultation_id:
            consultation = (
                db.query(models.ClinicalConsultation)
                .filter(
                    models.ClinicalConsultation.clinic_id == clinic_id,
                    models.ClinicalConsultation.patient_id == payload.patient_id,
                    models.ClinicalConsultation.deleted_at.is_(None),
                    models.ClinicalConsultation.status.in_(("scheduled", "in_progress")),
                )
                .order_by(models.ClinicalConsultation.created_at.desc())
                .first()
            )
            consultation_id = consultation.id if consultation else None

        if consultation_id:
            row.consultation_id = consultation_id
            NurseAssessmentService._sync_to_consultation(db, row, consultation_id)

        MedicalHistoryService.record_vitals(
            db,
            payload.patient_id,
            mh_schemas.PatientVitalSignsCreate(
                consultation_id=consultation_id,
                bp_systolic=payload.bp_systolic,
                bp_diastolic=payload.bp_diastolic,
                heart_rate=payload.heart_rate,
                temperature_c=payload.temperature_c,
                weight_kg=payload.weight_kg,
                height_cm=payload.height_cm,
                respiratory_rate=payload.respiratory_rate,
                bmi=bmi,
                notes=vitals_notes,
            ),
            actor,
            client_ip=client_ip,
        )

        db.commit()
        db.refresh(row)
        ClinicalAuditService.log(
            db,
            actor=actor,
            patient_id=payload.patient_id,
            action="create" if not existing else "update",
            resource_type="nurse_assessment",
            resource_id=row.id,
            client_ip=client_ip,
        )
        return row

    @staticmethod
    def _sync_to_consultation(
        db: Session, assessment: models.NurseAssessment, consultation_id: int
    ) -> None:
        consultation = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.id == consultation_id,
                models.ClinicalConsultation.deleted_at.is_(None),
            )
            .first()
        )
        if not consultation:
            return
        if assessment.reason_for_consultation:
            consultation.chief_complaint = assessment.reason_for_consultation.strip()
        combined = _combine_history(assessment)
        if combined:
            consultation.history = combined
        consultation.updated_at = datetime.utcnow()

    @staticmethod
    def apply_to_consultation(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        consultation: models.ClinicalConsultation,
    ) -> Optional[models.NurseAssessment]:
        assessment = NurseAssessmentService.get_latest(
            db, clinic_id=clinic_id, patient_id=patient_id
        )
        if not assessment:
            return None
        assessment.consultation_id = consultation.id
        if not consultation.chief_complaint and assessment.reason_for_consultation:
            consultation.chief_complaint = assessment.reason_for_consultation.strip()
        if not consultation.history:
            combined = _combine_history(assessment)
            if combined:
                consultation.history = combined
        consultation.updated_at = datetime.utcnow()
        db.flush()
        return assessment

    @staticmethod
    def dashboard_stats(db: Session, *, clinic_id: int) -> na_schemas.NurseDashboardStats:
        today_start = NurseAssessmentService._today_start()
        assessments_today = (
            db.query(models.NurseAssessment)
            .filter(
                models.NurseAssessment.clinic_id == clinic_id,
                models.NurseAssessment.deleted_at.is_(None),
                models.NurseAssessment.recorded_at >= today_start,
            )
            .count()
        )
        admissions_today = (
            db.query(models.Admission)
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.admitted_at >= today_start,
            )
            .count()
        )
        assessed_patient_ids = {
            r[0]
            for r in db.query(models.NurseAssessment.patient_id)
            .filter(
                models.NurseAssessment.clinic_id == clinic_id,
                models.NurseAssessment.deleted_at.is_(None),
                models.NurseAssessment.recorded_at >= today_start,
            )
            .distinct()
            .all()
        }
        pending = max(0, admissions_today - len(assessed_patient_ids))
        recent = (
            db.query(models.NurseAssessment)
            .options(joinedload(models.NurseAssessment.patient))
            .filter(
                models.NurseAssessment.clinic_id == clinic_id,
                models.NurseAssessment.deleted_at.is_(None),
            )
            .order_by(models.NurseAssessment.recorded_at.desc())
            .limit(8)
            .all()
        )
        return na_schemas.NurseDashboardStats(
            assessments_today=assessments_today,
            pending_admissions_today=pending,
            recent_assessments=[_serialize_assessment(r) for r in recent],
        )

    @staticmethod
    def serialize(row: models.NurseAssessment) -> na_schemas.NurseAssessmentResponse:
        return _serialize_assessment(row)

    @staticmethod
    def _priority_label(admission_type: Optional[str]) -> str:
        if admission_type == "emergency":
            return "Urgence"
        if admission_type == "hospitalization":
            return "Hospitalisation"
        if admission_type == "specialized_consultation":
            return "Consultation spécialisée"
        return "Routine"

    @staticmethod
    def _parse_services(services_json: Optional[str]) -> list[str]:
        if not services_json:
            return []
        try:
            import json

            data = json.loads(services_json)
            if isinstance(data, list):
                return [str(s) for s in data if s]
        except Exception:
            pass
        return []

    @staticmethod
    def get_patient_detail(db: Session, *, clinic_id: int, patient_id: int) -> models.Patient:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        patient = (
            db.query(models.Patient)
            .filter(
                models.Patient.id == patient_id,
                models.Patient.clinic_id == clinic_id,
                models.Patient.is_archived.is_(False),
            )
            .first()
        )
        if not patient:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient introuvable")
        return patient

    @staticmethod
    def list_assessments_today(db: Session, *, clinic_id: int) -> list[na_schemas.NurseAssessmentQueueRow]:
        today_start = NurseAssessmentService._today_start()
        rows = (
            db.query(models.NurseAssessment)
            .options(joinedload(models.NurseAssessment.patient))
            .filter(
                models.NurseAssessment.clinic_id == clinic_id,
                models.NurseAssessment.deleted_at.is_(None),
                models.NurseAssessment.recorded_at >= today_start,
            )
            .order_by(models.NurseAssessment.recorded_at.desc())
            .all()
        )
        out: list[na_schemas.NurseAssessmentQueueRow] = []
        for row in rows:
            patient = row.patient
            out.append(
                na_schemas.NurseAssessmentQueueRow(
                    assessment_id=row.id,
                    patient_id=row.patient_id,
                    patient_number=patient.patient_number if patient else None,
                    patient_name=f"{patient.last_name} {patient.first_name}".strip() if patient else "—",
                    nurse_name=row.nurse_name,
                    status="Évalué",
                    recorded_at=row.recorded_at,
                )
            )
        return out

    @staticmethod
    def list_pending_admissions_today(db: Session, *, clinic_id: int) -> list[na_schemas.NursePendingAdmissionRow]:
        today_start = NurseAssessmentService._today_start()
        assessed_patient_ids = {
            r[0]
            for r in db.query(models.NurseAssessment.patient_id)
            .filter(
                models.NurseAssessment.clinic_id == clinic_id,
                models.NurseAssessment.deleted_at.is_(None),
                models.NurseAssessment.recorded_at >= today_start,
            )
            .distinct()
            .all()
        }
        admissions = (
            db.query(models.Admission)
            .options(joinedload(models.Admission.patient))
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.admitted_at >= today_start,
                models.Admission.status.notin_(["discharged", "cancelled"]),
            )
            .order_by(models.Admission.admitted_at.asc())
            .all()
        )
        out: list[na_schemas.NursePendingAdmissionRow] = []
        for adm in admissions:
            if adm.patient_id in assessed_patient_ids:
                continue
            patient = adm.patient
            services = NurseAssessmentService._parse_services(adm.services_json)
            if not services and adm.department:
                services = [adm.department]
            out.append(
                na_schemas.NursePendingAdmissionRow(
                    admission_id=adm.id,
                    patient_id=adm.patient_id,
                    patient_number=patient.patient_number if patient else None,
                    patient_name=f"{patient.last_name} {patient.first_name}".strip() if patient else "—",
                    admitted_at=adm.admitted_at,
                    services=services,
                    priority=NurseAssessmentService._priority_label(adm.admission_type),
                    department=adm.department,
                )
            )
        return out
