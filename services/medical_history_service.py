"""Permanent medical history, timeline, and follow-up orchestration."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
import schemas.medical_history as mh_schemas
from models.user import User
from services.clinical_audit_service import ClinicalAuditService
from services.patient_record_access import PatientRecordAccessPolicy

INTERVAL_DAYS = {
    "7d": 7,
    "15d": 15,
    "1m": 30,
    "3m": 90,
    "6m": 180,
}


def _not_deleted(model):
    """SQLAlchemy filter: row not soft-deleted."""
    return getattr(model, "deleted_at").is_(None)


def ensure_medical_record(db: Session, patient_id: int) -> models.PatientMedicalRecord:
    record = (
        db.query(models.PatientMedicalRecord)
        .filter(models.PatientMedicalRecord.patient_id == patient_id)
        .first()
    )
    if record:
        return record
    record = models.PatientMedicalRecord(patient_id=patient_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def _patient_display_name(patient: models.Patient) -> str:
    return f"{patient.first_name or ''} {patient.last_name or ''}".strip() or f"Patient #{patient.id}"


def _doctor_name(db: Session, doctor_id: int) -> str | None:
    doc = db.query(models.Doctor).filter(models.Doctor.id == doctor_id).first()
    return doc.name if doc else None


def _resolve_follow_up_date(interval_type: str, custom_date: date | None) -> date:
    if interval_type == "custom":
        if not custom_date:
            raise HTTPException(status_code=400, detail="scheduled_date required for custom interval")
        return custom_date
    days = INTERVAL_DAYS.get(interval_type)
    if days is None:
        raise HTTPException(status_code=400, detail=f"Invalid interval_type: {interval_type}")
    return date.today() + timedelta(days=days)


def _refresh_follow_up_statuses(db: Session, *, clinic_id: int | None = None) -> None:
    today = date.today()
    q = db.query(models.FollowUpSchedule).filter(
        models.FollowUpSchedule.deleted_at.is_(None),
        models.FollowUpSchedule.status == "scheduled",
        models.FollowUpSchedule.scheduled_date < today,
    )
    if clinic_id is not None:
        q = q.filter(models.FollowUpSchedule.clinic_id == clinic_id)
    for fu in q.all():
        fu.status = "overdue"
        fu.updated_at = datetime.utcnow()
    db.commit()


class MedicalHistoryService:
    @staticmethod
    def get_or_create_record(db: Session, patient_id: int) -> models.PatientMedicalRecord:
        return ensure_medical_record(db, patient_id)

    @staticmethod
    def update_record(
        db: Session,
        patient_id: int,
        payload: mh_schemas.PatientMedicalRecordUpdate,
        current_user: User,
        *,
        client_ip: str | None = None,
    ) -> mh_schemas.PatientMedicalRecordResponse:
        PatientRecordAccessPolicy.assert_can_write_clinical(db, current_user, patient_id)
        record = ensure_medical_record(db, patient_id)
        if payload.blood_type is not None:
            record.blood_type = payload.blood_type
        if payload.general_notes is not None:
            record.general_notes = payload.general_notes
        record.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(record)
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="update",
            resource_type="medical_record",
            resource_id=record.id,
            client_ip=client_ip,
        )
        return record

    @staticmethod
    def add_allergy(
        db: Session,
        patient_id: int,
        payload: mh_schemas.PatientAllergyCreate,
        current_user: User,
        *,
        client_ip: str | None = None,
    ) -> models.PatientAllergy:
        PatientRecordAccessPolicy.assert_can_write_clinical(db, current_user, patient_id)
        ensure_medical_record(db, patient_id)
        allergy = models.PatientAllergy(
            patient_id=patient_id,
            allergen=payload.allergen.strip(),
            severity=payload.severity,
            reaction=payload.reaction,
            recorded_by_user_id=current_user.id,
        )
        db.add(allergy)
        db.commit()
        db.refresh(allergy)
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="create",
            resource_type="patient_allergy",
            resource_id=allergy.id,
            client_ip=client_ip,
        )
        return allergy

    @staticmethod
    def soft_delete_allergy(
        db: Session,
        patient_id: int,
        allergy_id: int,
        current_user: User,
        *,
        client_ip: str | None = None,
    ) -> None:
        PatientRecordAccessPolicy.assert_can_write_clinical(db, current_user, patient_id)
        allergy = (
            db.query(models.PatientAllergy)
            .filter(
                models.PatientAllergy.id == allergy_id,
                models.PatientAllergy.patient_id == patient_id,
                models.PatientAllergy.deleted_at.is_(None),
            )
            .first()
        )
        if not allergy:
            raise HTTPException(status_code=404, detail="Allergy not found")
        allergy.is_active = False
        allergy.deleted_at = datetime.utcnow()
        db.commit()
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="soft_delete",
            resource_type="patient_allergy",
            resource_id=allergy_id,
            client_ip=client_ip,
        )

    @staticmethod
    def add_chronic_condition(
        db: Session,
        patient_id: int,
        payload: mh_schemas.PatientChronicConditionCreate,
        current_user: User,
        *,
        client_ip: str | None = None,
    ) -> models.PatientChronicCondition:
        PatientRecordAccessPolicy.assert_can_write_clinical(db, current_user, patient_id)
        ensure_medical_record(db, patient_id)
        cond = models.PatientChronicCondition(
            patient_id=patient_id,
            condition_name=payload.condition_name.strip(),
            diagnosed_at=payload.diagnosed_at,
            status=payload.status,
            notes=payload.notes,
            recorded_by_user_id=current_user.id,
        )
        db.add(cond)
        db.commit()
        db.refresh(cond)
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="create",
            resource_type="chronic_condition",
            resource_id=cond.id,
            client_ip=client_ip,
        )
        return cond

    @staticmethod
    def record_vitals(
        db: Session,
        patient_id: int,
        payload: mh_schemas.PatientVitalSignsCreate,
        current_user: User,
        *,
        client_ip: str | None = None,
    ) -> models.PatientVitalSigns:
        PatientRecordAccessPolicy.assert_can_write_clinical(db, current_user, patient_id)
        ensure_medical_record(db, patient_id)
        if payload.consultation_id:
            c = (
                db.query(models.ClinicalConsultation)
                .filter(
                    models.ClinicalConsultation.id == payload.consultation_id,
                    models.ClinicalConsultation.patient_id == patient_id,
                    models.ClinicalConsultation.deleted_at.is_(None),
                )
                .first()
            )
            if not c:
                raise HTTPException(status_code=404, detail="Consultation not found")
        vitals = models.PatientVitalSigns(
            patient_id=patient_id,
            consultation_id=payload.consultation_id,
            bp_systolic=payload.bp_systolic,
            bp_diastolic=payload.bp_diastolic,
            heart_rate=payload.heart_rate,
            temperature_c=payload.temperature_c,
            weight_kg=payload.weight_kg,
            height_cm=payload.height_cm,
            spo2=payload.spo2,
            notes=payload.notes,
            recorded_by_user_id=current_user.id,
        )
        db.add(vitals)
        db.commit()
        db.refresh(vitals)
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="create",
            resource_type="vital_signs",
            resource_id=vitals.id,
            client_ip=client_ip,
        )
        return vitals

    @staticmethod
    def schedule_follow_up(
        db: Session,
        *,
        patient_id: int,
        clinic_id: int,
        consultation_id: int | None,
        doctor_id: int,
        payload: mh_schemas.FollowUpScheduleCreate,
        current_user: User,
        client_ip: str | None = None,
    ) -> models.FollowUpSchedule:
        PatientRecordAccessPolicy.assert_can_write_clinical(db, current_user, patient_id)
        ensure_medical_record(db, patient_id)
        scheduled = _resolve_follow_up_date(payload.interval_type, payload.scheduled_date)
        fu = models.FollowUpSchedule(
            patient_id=patient_id,
            clinic_id=clinic_id,
            consultation_id=consultation_id,
            doctor_id=doctor_id,
            scheduled_date=scheduled,
            interval_type=payload.interval_type,
            visit_type=payload.visit_type,
            reason=payload.reason,
            clinical_notes=payload.clinical_notes,
            status="scheduled",
            created_by_user_id=current_user.id,
        )
        db.add(fu)
        db.commit()
        db.refresh(fu)
        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="create",
            resource_type="follow_up",
            resource_id=fu.id,
            client_ip=client_ip,
        )
        return fu

    @staticmethod
    def snapshot_consultation_to_dossier(
        db: Session,
        consultation: models.ClinicalConsultation,
        *,
        actor: User | None = None,
    ) -> None:
        """Persist consultation outcome into permanent dossier (never deleted)."""
        ensure_medical_record(db, consultation.patient_id)
        if consultation.diagnosis or consultation.treatment_plan:
            summary = models.ConsultationSummary(
                patient_id=consultation.patient_id,
                doctor_id=consultation.doctor_id,
                appointment_id=consultation.appointment_id,
                diagnostic=consultation.diagnosis,
                traitement=consultation.treatment_plan,
                recommandations=None,
            )
            db.add(summary)
        note_parts = []
        if consultation.chief_complaint:
            note_parts.append(f"Motif: {consultation.chief_complaint}")
        if consultation.examination:
            note_parts.append(f"Examen: {consultation.examination}")
        if consultation.history:
            note_parts.append(f"Antécédents: {consultation.history}")
        if note_parts:
            db.add(
                models.ClinicalNote(
                    patient_id=consultation.patient_id,
                    doctor_id=consultation.doctor_id,
                    appointment_id=consultation.appointment_id,
                    note_type="consultation",
                    contenu="\n".join(note_parts),
                )
            )
        db.commit()

    @staticmethod
    def build_grouped_timeline(db: Session, patient_id: int) -> list[mh_schemas.TimelineDayGroup]:
        """Chronological timeline grouped by day for UI."""
        day_map: dict[date, list[mh_schemas.TimelineDayEvent]] = {}

        def add_event(d: date, event_type: str, title: str, details: dict) -> None:
            day_map.setdefault(d, []).append(
                mh_schemas.TimelineDayEvent(event_type=event_type, title=title, details=details)
            )

        consultations = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.patient_id == patient_id,
                models.ClinicalConsultation.deleted_at.is_(None),
            )
            .order_by(models.ClinicalConsultation.started_at.asc())
            .all()
        )
        for c in consultations:
            ts = c.completed_at or c.started_at or c.created_at
            d = ts.date() if ts else date.today()
            rx_list = []
            for rx in c.prescriptions or []:
                if rx.deleted_at:
                    continue
                meds = ", ".join(i.medication_name for i in (rx.items or []))
                rx_list.append(meds)
            lab_list = []
            for lo in c.lab_orders or []:
                if lo.deleted_at:
                    continue
                lab_list.append(lo.test_name)
            visit_label = "Consultation" if c.status == "completed" else f"Consultation ({c.status})"
            add_event(
                d,
                "consultation",
                visit_label,
                {
                    "consultation_id": c.id,
                    "diagnosis": c.diagnosis,
                    "treatment_plan": c.treatment_plan,
                    "prescriptions": rx_list,
                    "lab_orders": lab_list,
                    "chief_complaint": c.chief_complaint,
                },
            )

        for fu in (
            db.query(models.FollowUpSchedule)
            .filter(
                models.FollowUpSchedule.patient_id == patient_id,
                models.FollowUpSchedule.deleted_at.is_(None),
            )
            .all()
        ):
            label = "Suivi" if fu.visit_type == "follow_up" else "Consultation"
            add_event(
                fu.scheduled_date,
                "follow_up",
                label,
                {
                    "follow_up_id": fu.id,
                    "reason": fu.reason,
                    "clinical_notes": fu.clinical_notes,
                    "status": fu.status,
                },
            )

        for note in (
            db.query(models.ClinicalNote)
            .filter(models.ClinicalNote.patient_id == patient_id)
            .all()
        ):
            if note.note_type == "consultation":
                continue  # already covered by CIS snapshot
            add_event(
                note.created_at.date(),
                "clinical_note",
                f"Note ({note.note_type})",
                {"contenu": note.contenu},
            )

        groups = []
        for d in sorted(day_map.keys(), reverse=True):
            groups.append(mh_schemas.TimelineDayGroup(date=d, events=day_map[d]))
        return groups

    @staticmethod
    def get_full_history(
        db: Session,
        patient_id: int,
        current_user: User,
        *,
        client_ip: str | None = None,
    ) -> mh_schemas.PatientMedicalHistoryResponse:
        patient = PatientRecordAccessPolicy.assert_can_read_dossier(db, current_user, patient_id)
        clinic_id = PatientRecordAccessPolicy.dossier_clinic_id(db, current_user, patient)
        record = (
            db.query(models.PatientMedicalRecord)
            .filter(models.PatientMedicalRecord.patient_id == patient_id)
            .first()
        )

        allergies = (
            db.query(models.PatientAllergy)
            .filter(
                models.PatientAllergy.patient_id == patient_id,
                models.PatientAllergy.deleted_at.is_(None),
                models.PatientAllergy.is_active.is_(True),
            )
            .order_by(models.PatientAllergy.created_at.desc())
            .all()
        )
        conditions = (
            db.query(models.PatientChronicCondition)
            .filter(
                models.PatientChronicCondition.patient_id == patient_id,
                models.PatientChronicCondition.deleted_at.is_(None),
            )
            .order_by(models.PatientChronicCondition.created_at.desc())
            .all()
        )
        vitals = (
            db.query(models.PatientVitalSigns)
            .filter(
                models.PatientVitalSigns.patient_id == patient_id,
                models.PatientVitalSigns.deleted_at.is_(None),
            )
            .order_by(models.PatientVitalSigns.recorded_at.desc())
            .all()
        )
        consultations_raw = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.patient_id == patient_id,
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.deleted_at.is_(None),
            )
            .order_by(models.ClinicalConsultation.started_at.desc())
            .all()
        )
        consultations = []
        for c in consultations_raw:
            ts = c.completed_at or c.started_at or c.created_at
            rx_payload = []
            for rx in c.prescriptions or []:
                if rx.deleted_at:
                    continue
                rx_payload.append(
                    {
                        "id": rx.id,
                        "medications": [
                            {
                                "name": i.medication_name,
                                "dosage": i.dosage,
                                "frequency": i.frequency,
                            }
                            for i in (rx.items or [])
                        ],
                        "status": rx.status,
                        "date": (rx.created_at.isoformat() if rx.created_at else None),
                    }
                )
            lab_payload = []
            for lo in c.lab_orders or []:
                if lo.deleted_at:
                    continue
                result = (lo.results or [None])[0] if lo.results else None
                lab_payload.append(
                    {
                        "id": lo.id,
                        "test_name": lo.test_name,
                        "status": lo.status,
                        "result_summary": result.result_summary if result else None,
                        "interpretation": result.interpretation if result else None,
                    }
                )
            consultations.append(
                mh_schemas.ConsultationHistoryItem(
                    id=c.id,
                    date=ts or datetime.utcnow(),
                    doctor_name=_doctor_name(db, c.doctor_id),
                    diagnosis=c.diagnosis,
                    treatment_plan=c.treatment_plan,
                    chief_complaint=c.chief_complaint,
                    status=c.status,
                    prescriptions=rx_payload,
                    lab_orders=lab_payload,
                )
            )

        all_prescriptions = []
        for rx in (
            db.query(models.Prescription)
            .filter(
                models.Prescription.patient_id == patient_id,
                models.Prescription.clinic_id == clinic_id,
                models.Prescription.deleted_at.is_(None),
            )
            .order_by(models.Prescription.created_at.desc())
            .all()
        ):
            all_prescriptions.append(
                {
                    "id": rx.id,
                    "date": rx.created_at.isoformat() if rx.created_at else None,
                    "medications": [
                        {"name": i.medication_name, "dosage": i.dosage, "frequency": i.frequency}
                        for i in (rx.items or [])
                    ],
                    "status": rx.status,
                }
            )

        lab_results = []
        for lo in (
            db.query(models.LabOrder)
            .filter(
                models.LabOrder.patient_id == patient_id,
                models.LabOrder.clinic_id == clinic_id,
                models.LabOrder.deleted_at.is_(None),
            )
            .order_by(models.LabOrder.created_at.desc())
            .all()
        ):
            for result in lo.results or []:
                if result.status == "validated":
                    lab_results.append(
                        {
                            "lab_order_id": lo.id,
                            "test_name": lo.test_name,
                            "result_summary": result.result_summary,
                            "reference_range": result.reference_range,
                            "interpretation": result.interpretation,
                            "validated_at": (
                                result.validated_at.isoformat() if result.validated_at else None
                            ),
                        }
                    )

        follow_ups = (
            db.query(models.FollowUpSchedule)
            .filter(
                models.FollowUpSchedule.patient_id == patient_id,
                models.FollowUpSchedule.deleted_at.is_(None),
            )
            .order_by(models.FollowUpSchedule.scheduled_date.asc())
            .all()
        )
        fu_responses = [
            mh_schemas.FollowUpScheduleResponse(
                id=f.id,
                patient_id=f.patient_id,
                clinic_id=f.clinic_id,
                consultation_id=f.consultation_id,
                doctor_id=f.doctor_id,
                doctor_name=_doctor_name(db, f.doctor_id),
                patient_name=_patient_display_name(patient),
                scheduled_date=f.scheduled_date,
                interval_type=f.interval_type,
                visit_type=f.visit_type,
                reason=f.reason,
                clinical_notes=f.clinical_notes,
                status=f.status,
                follow_up_appointment_id=f.follow_up_appointment_id,
                created_at=f.created_at,
            )
            for f in follow_ups
        ]

        timeline = MedicalHistoryService.build_grouped_timeline(db, patient_id)

        ClinicalAuditService.log(
            db,
            actor=current_user,
            patient_id=patient_id,
            action="read",
            resource_type="medical_history",
            client_ip=client_ip,
        )

        return mh_schemas.PatientMedicalHistoryResponse(
            patient_id=patient_id,
            patient_name=_patient_display_name(patient),
            medical_record=record,
            allergies=allergies,
            chronic_conditions=conditions,
            consultations=consultations,
            prescriptions=all_prescriptions,
            lab_results=lab_results,
            vital_signs=vitals,
            follow_ups=fu_responses,
            timeline=timeline,
        )

    @staticmethod
    def reception_follow_up_summary(
        db: Session, *, clinic_id: int
    ) -> mh_schemas.FollowUpReceptionSummary:
        _refresh_follow_up_statuses(db, clinic_id=clinic_id)
        today = date.today()
        horizon = today + timedelta(days=30)

        base = (
            db.query(models.FollowUpSchedule)
            .filter(
                models.FollowUpSchedule.clinic_id == clinic_id,
                models.FollowUpSchedule.deleted_at.is_(None),
                models.FollowUpSchedule.status.in_(("scheduled", "overdue")),
            )
            .order_by(models.FollowUpSchedule.scheduled_date.asc())
            .all()
        )

        def to_resp(f: models.FollowUpSchedule) -> mh_schemas.FollowUpScheduleResponse:
            p = f.patient
            return mh_schemas.FollowUpScheduleResponse(
                id=f.id,
                patient_id=f.patient_id,
                clinic_id=f.clinic_id,
                consultation_id=f.consultation_id,
                doctor_id=f.doctor_id,
                doctor_name=_doctor_name(db, f.doctor_id),
                patient_name=_patient_display_name(p) if p else None,
                scheduled_date=f.scheduled_date,
                interval_type=f.interval_type,
                visit_type=f.visit_type,
                reason=f.reason,
                clinical_notes=f.clinical_notes,
                status=f.status,
                follow_up_appointment_id=f.follow_up_appointment_id,
                created_at=f.created_at,
            )

        due_today = [to_resp(f) for f in base if f.scheduled_date == today]
        overdue = [to_resp(f) for f in base if f.status == "overdue"]
        upcoming = [
            to_resp(f)
            for f in base
            if f.scheduled_date > today and f.scheduled_date <= horizon and f.status == "scheduled"
        ]
        return mh_schemas.FollowUpReceptionSummary(
            due_today=due_today, overdue=overdue, upcoming=upcoming
        )
