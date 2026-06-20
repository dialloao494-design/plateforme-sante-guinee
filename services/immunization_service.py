"""PEV immunization — schedule, history, due and missed vaccines."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

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
        dose_number: Optional[int] = None,
        batch_number: Optional[str] = None,
        next_appointment_date: Optional[date] = None,
        vaccinator_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> models.ImmunizationRecord:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        display_vaccinator = vaccinator_name or (actor.email if actor else None)
        row = models.ImmunizationRecord(
            clinic_id=clinic_id,
            patient_id=patient_id,
            vaccine_code=vaccine_code.strip().upper(),
            vaccine_name=vaccine_name.strip(),
            dose_label=dose_label,
            dose_number=dose_number,
            batch_number=batch_number,
            administered_at=administered_at,
            next_appointment_date=next_appointment_date,
            vaccinator_name=display_vaccinator,
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

    @staticmethod
    def _age_group_label(age_months: int) -> str:
        if age_months < 12:
            return "0-11 mois"
        if age_months < 24:
            return "12-23 mois"
        if age_months < 60:
            return "24-59 mois"
        return "5 ans et plus"

    @staticmethod
    def dashboard_stats(db: Session, *, clinic_id: int) -> dict:
        today = date.today()
        month_start = today.replace(day=1)
        base = db.query(models.ImmunizationRecord).filter(
            models.ImmunizationRecord.clinic_id == clinic_id,
            models.ImmunizationRecord.deleted_at.is_(None),
        )
        daily = base.filter(models.ImmunizationRecord.administered_at == today).count()
        monthly_rows = (
            base.filter(models.ImmunizationRecord.administered_at >= month_start)
            .options(joinedload(models.ImmunizationRecord.patient))
            .all()
        )
        by_vaccine: dict[str, int] = {}
        by_age: dict[str, int] = {}
        for row in monthly_rows:
            by_vaccine[row.vaccine_name] = by_vaccine.get(row.vaccine_name, 0) + 1
            patient = row.patient
            if patient:
                age_m = _patient_age_months(patient, row.administered_at)
                label = ImmunizationService._age_group_label(age_m)
                by_age[label] = by_age.get(label, 0) + 1
        return {
            "daily_vaccinations": daily,
            "monthly_vaccinations": len(monthly_rows),
            "by_age_group": by_age,
            "by_vaccine_type": by_vaccine,
        }

    @staticmethod
    def monthly_report(db: Session, *, clinic_id: int, year: int, month: int) -> dict:
        from calendar import monthrange

        start = date(year, month, 1)
        end = date(year, month, monthrange(year, month)[1])
        rows = (
            db.query(models.ImmunizationRecord)
            .options(joinedload(models.ImmunizationRecord.patient))
            .filter(
                models.ImmunizationRecord.clinic_id == clinic_id,
                models.ImmunizationRecord.deleted_at.is_(None),
                models.ImmunizationRecord.administered_at >= start,
                models.ImmunizationRecord.administered_at <= end,
            )
            .order_by(models.ImmunizationRecord.administered_at)
            .all()
        )
        by_vaccine: dict[str, int] = {}
        by_age: dict[str, int] = {}
        for row in rows:
            by_vaccine[row.vaccine_name] = by_vaccine.get(row.vaccine_name, 0) + 1
            if row.patient:
                age_m = _patient_age_months(row.patient, row.administered_at)
                label = ImmunizationService._age_group_label(age_m)
                by_age[label] = by_age.get(label, 0) + 1
        return {
            "year": year,
            "month": month,
            "total_vaccinations": len(rows),
            "by_vaccine_type": by_vaccine,
            "by_age_group": by_age,
            "records": rows,
        }
