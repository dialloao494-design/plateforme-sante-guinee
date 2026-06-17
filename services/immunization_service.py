"""PEV immunization — schedule, history, due and missed vaccines."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from core.tenant import assert_patient_in_clinic
from data.pev_schedule import DEFAULT_PEV_SCHEDULE
from models.user import User


def _patient_age_months(patient: models.Patient, on_date: date | None = None) -> int:
    on_date = on_date or date.today()
    if patient.date_of_birth:
        delta = on_date - patient.date_of_birth
        return max(0, delta.days // 30)
    if patient.age is not None:
        return int(patient.age) * 12
    return 0


def _due_date_from_birth(patient: models.Patient, age_months: int) -> date:
    if patient.date_of_birth:
        return patient.date_of_birth + timedelta(days=age_months * 30)
    return date.today()


class ImmunizationService:
    @staticmethod
    def ensure_schedule_seeded(db: Session) -> None:
        existing = db.query(models.VaccineScheduleItem).count()
        if existing:
            return
        for item in DEFAULT_PEV_SCHEDULE:
            db.add(
                models.VaccineScheduleItem(
                    vaccine_code=str(item["vaccine_code"]),
                    vaccine_name=str(item["vaccine_name"]),
                    dose_label=str(item["dose_label"]),
                    age_months=int(item["age_months"]),
                    grace_days=14,
                    is_active=True,
                )
            )
        db.commit()

    @staticmethod
    def list_schedule(db: Session) -> List[models.VaccineScheduleItem]:
        ImmunizationService.ensure_schedule_seeded(db)
        return (
            db.query(models.VaccineScheduleItem)
            .filter(models.VaccineScheduleItem.is_active.is_(True))
            .order_by(models.VaccineScheduleItem.age_months, models.VaccineScheduleItem.id)
            .all()
        )

    @staticmethod
    def list_history(db: Session, *, clinic_id: int, patient_id: int) -> List[models.ImmunizationRecord]:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        return (
            db.query(models.ImmunizationRecord)
            .filter(
                models.ImmunizationRecord.patient_id == patient_id,
                models.ImmunizationRecord.clinic_id == clinic_id,
                models.ImmunizationRecord.deleted_at.is_(None),
            )
            .order_by(models.ImmunizationRecord.administered_at.desc())
            .all()
        )

    @staticmethod
    def record_vaccination(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        actor: User,
        vaccine_code: str,
        vaccine_name: str,
        administered_at: date,
        dose_label: Optional[str] = None,
        batch_number: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> models.ImmunizationRecord:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        row = models.ImmunizationRecord(
            clinic_id=clinic_id,
            patient_id=patient_id,
            vaccine_code=vaccine_code.strip().upper(),
            vaccine_name=vaccine_name.strip(),
            dose_label=dose_label,
            batch_number=batch_number,
            administered_at=administered_at,
            administered_by_user_id=actor.id,
            notes=notes,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def compute_due_and_missed(
        db: Session, *, clinic_id: int, patient_id: int
    ) -> dict[str, list[dict]]:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        ImmunizationService.ensure_schedule_seeded(db)
        patient = db.query(models.Patient).filter(models.Patient.id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        history = ImmunizationService.list_history(db, clinic_id=clinic_id, patient_id=patient_id)
        done_keys = {
            (r.vaccine_code.upper(), (r.dose_label or "").strip().lower()) for r in history
        }
        schedule = ImmunizationService.list_schedule(db)
        today = date.today()
        age_m = _patient_age_months(patient, today)

        due: list[dict] = []
        missed: list[dict] = []
        upcoming: list[dict] = []

        for item in schedule:
            key = (item.vaccine_code.upper(), item.dose_label.strip().lower())
            if key in done_keys:
                continue
            due_date = _due_date_from_birth(patient, item.age_months)
            grace_end = due_date + timedelta(days=item.grace_days)
            entry = {
                "vaccine_code": item.vaccine_code,
                "vaccine_name": item.vaccine_name,
                "dose_label": item.dose_label,
                "age_months": item.age_months,
                "due_date": due_date.isoformat(),
            }
            if today > grace_end:
                missed.append(entry)
            elif age_m >= item.age_months:
                due.append(entry)
            else:
                upcoming.append(entry)

        return {"due": due, "missed": missed, "upcoming": upcoming}
