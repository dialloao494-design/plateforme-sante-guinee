"""Nursing care procedures — soins infirmiers."""

from __future__ import annotations

from calendar import monthrange
from collections import defaultdict
from datetime import date, datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

import models
from core.tenant import assert_patient_in_clinic
from models.user import User
from services.clinical_register_utils import patient_snapshot, serialize_row, wrap_register_rows


PROCEDURE_TYPES = ("injection", "perfusion", "dressing", "suture", "other")


class NursingCareService:
    @staticmethod
    def list_procedures(
        db: Session,
        *,
        clinic_id: int,
        procedure_date: date | None = None,
        limit: int = 200,
    ) -> List[models.NursingProcedure]:
        q = db.query(models.NursingProcedure).options(joinedload(models.NursingProcedure.patient)).filter(
            models.NursingProcedure.clinic_id == clinic_id,
            models.NursingProcedure.deleted_at.is_(None),
        )
        if procedure_date:
            q = q.filter(models.NursingProcedure.procedure_date == procedure_date)
        return q.order_by(
            models.NursingProcedure.procedure_date.desc(),
            models.NursingProcedure.id.desc(),
        ).limit(limit).all()

    @staticmethod
    def record_procedure(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        actor: User,
        procedure_type: str,
        procedure_date: date,
        procedure_time: Optional[str] = None,
        nurse_name: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> models.NursingProcedure:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        ptype = procedure_type.strip().lower()
        if ptype not in PROCEDURE_TYPES:
            raise HTTPException(status_code=400, detail=f"Invalid procedure_type: {procedure_type}")
        display_name = nurse_name or (actor.email if actor else None)
        row = models.NursingProcedure(
            clinic_id=clinic_id,
            patient_id=patient_id,
            procedure_type=ptype,
            procedure_date=procedure_date,
            procedure_time=procedure_time,
            nurse_user_id=actor.id,
            nurse_name=display_name,
            notes=notes,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def _count_by_type(rows: list[models.NursingProcedure]) -> dict[str, int]:
        counts = {t: 0 for t in PROCEDURE_TYPES}
        for row in rows:
            counts[row.procedure_type] = counts.get(row.procedure_type, 0) + 1
        return counts

    @staticmethod
    def dashboard_stats(db: Session, *, clinic_id: int) -> dict:
        today = date.today()
        month_start = today.replace(day=1)
        base = db.query(models.NursingProcedure).filter(
            models.NursingProcedure.clinic_id == clinic_id,
            models.NursingProcedure.deleted_at.is_(None),
        )
        daily = base.filter(models.NursingProcedure.procedure_date == today).count()
        monthly_rows = base.filter(models.NursingProcedure.procedure_date >= month_start).all()
        by_type = NursingCareService._count_by_type(monthly_rows)
        return {
            "daily_procedures": daily,
            "monthly_procedures": len(monthly_rows),
            "injections": by_type.get("injection", 0),
            "perfusions": by_type.get("perfusion", 0),
            "dressings": by_type.get("dressing", 0),
            "sutures": by_type.get("suture", 0),
            "other": by_type.get("other", 0),
            "by_type": by_type,
        }

    @staticmethod
    def list_register(db: Session, *, clinic_id: int, year: int, month: int) -> list[dict]:
        start = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end = date(year, month, last_day)
        rows = (
            db.query(models.NursingProcedure)
            .options(joinedload(models.NursingProcedure.patient))
            .filter(
                models.NursingProcedure.clinic_id == clinic_id,
                models.NursingProcedure.deleted_at.is_(None),
                models.NursingProcedure.procedure_date >= start,
                models.NursingProcedure.procedure_date <= end,
            )
            .order_by(models.NursingProcedure.procedure_date, models.NursingProcedure.id)
            .all()
        )
        return [
            serialize_row(
                e,
                ["id", "procedure_type", "procedure_date", "procedure_time", "nurse_name", "notes"],
            )
            for e in wrap_register_rows(rows, on_date_attr="procedure_date")
        ]

    @staticmethod
    def list_patient_history(db: Session, *, clinic_id: int, patient_id: int) -> List[models.NursingProcedure]:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        return (
            db.query(models.NursingProcedure)
            .filter(
                models.NursingProcedure.clinic_id == clinic_id,
                models.NursingProcedure.patient_id == patient_id,
                models.NursingProcedure.deleted_at.is_(None),
            )
            .order_by(models.NursingProcedure.procedure_date.desc())
            .all()
        )

    @staticmethod
    def monthly_report(db: Session, *, clinic_id: int, year: int, month: int) -> dict:
        start = date(year, month, 1)
        last_day = monthrange(year, month)[1]
        end = date(year, month, last_day)
        rows = (
            db.query(models.NursingProcedure)
            .options(joinedload(models.NursingProcedure.patient))
            .filter(
                models.NursingProcedure.clinic_id == clinic_id,
                models.NursingProcedure.deleted_at.is_(None),
                models.NursingProcedure.procedure_date >= start,
                models.NursingProcedure.procedure_date <= end,
            )
            .all()
        )
        by_type = NursingCareService._count_by_type(rows)
        daily: dict[int, dict[str, int]] = defaultdict(lambda: {t: 0 for t in PROCEDURE_TYPES})
        for row in rows:
            day = row.procedure_date.day
            daily[day][row.procedure_type] = daily[day].get(row.procedure_type, 0) + 1
        daily_tally = [
            {"day": day, **counts, "total": sum(counts.values())}
            for day, counts in sorted(daily.items())
        ]
        register_rows = [
            serialize_row(
                e,
                [
                    "id",
                    "procedure_type",
                    "procedure_date",
                    "procedure_time",
                    "nurse_name",
                    "notes",
                ],
            )
            for e in wrap_register_rows(
                sorted(rows, key=lambda r: (r.procedure_date, r.id)),
                on_date_attr="procedure_date",
            )
        ]
        return {
            "year": year,
            "month": month,
            "clinic_id": clinic_id,
            "total_procedures": len(rows),
            "by_type": by_type,
            "daily_tally": daily_tally,
            "register_rows": register_rows,
        }
