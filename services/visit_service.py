"""Clinical visit lifecycle — ties encounter services together."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

import models


class VisitService:
    @staticmethod
    def ensure_for_consultation(db: Session, consultation: models.ClinicalConsultation) -> models.ClinicalVisit:
        existing = (
            db.query(models.ClinicalVisit)
            .filter(models.ClinicalVisit.consultation_id == consultation.id)
            .first()
        )
        if existing:
            return existing
        visit = models.ClinicalVisit(
            clinic_id=consultation.clinic_id,
            patient_id=consultation.patient_id,
            appointment_id=consultation.appointment_id,
            consultation_id=consultation.id,
            status="open",
            started_at=consultation.started_at or datetime.utcnow(),
        )
        db.add(visit)
        db.commit()
        db.refresh(visit)
        return visit

    @staticmethod
    def get_or_create_for_patient_clinic(
        db: Session, *, clinic_id: int, patient_id: int, appointment_id: int | None = None
    ) -> models.ClinicalVisit:
        from fastapi import HTTPException

        patient = (
            db.query(models.Patient)
            .filter(models.Patient.id == patient_id, models.Patient.clinic_id == clinic_id)
            .first()
        )
        if not patient:
            raise HTTPException(
                status_code=403,
                detail="Patient does not belong to this clinic",
            )
        q = db.query(models.ClinicalVisit).filter(
            models.ClinicalVisit.clinic_id == clinic_id,
            models.ClinicalVisit.patient_id == patient_id,
            models.ClinicalVisit.status == "open",
        )
        if appointment_id:
            q = q.filter(models.ClinicalVisit.appointment_id == appointment_id)
        visit = q.order_by(models.ClinicalVisit.created_at.desc()).first()
        if visit:
            return visit
        visit = models.ClinicalVisit(
            clinic_id=clinic_id,
            patient_id=patient_id,
            appointment_id=appointment_id,
            status="open",
        )
        db.add(visit)
        db.commit()
        db.refresh(visit)
        return visit

    @staticmethod
    def link_admission(db: Session, visit: models.ClinicalVisit, admission_id: int) -> None:
        visit.admission_id = admission_id
        db.commit()

    @staticmethod
    def mark_discharged(db: Session, visit: models.ClinicalVisit) -> None:
        visit.status = "discharged"
        visit.discharged_at = datetime.utcnow()
        visit.closed_at = datetime.utcnow()
        db.commit()

    @staticmethod
    def mark_archived(db: Session, visit: models.ClinicalVisit) -> None:
        visit.status = "archived"
        if not visit.closed_at:
            visit.closed_at = datetime.utcnow()
        db.commit()
