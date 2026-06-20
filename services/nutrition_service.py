"""Nutrition assessment service — child growth monitoring."""

from __future__ import annotations

from datetime import date, datetime
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

import models
from core.tenant import assert_patient_in_clinic
from models.user import User


def _classify_muac(muac_cm: Optional[float]) -> Optional[str]:
    if muac_cm is None:
        return None
    if muac_cm < 11.5:
        return "severe_malnutrition"
    if muac_cm < 12.5:
        return "moderate_malnutrition"
    return "normal"


class NutritionService:
    @staticmethod
    def list_history(db: Session, *, clinic_id: int, patient_id: int) -> List[models.NutritionAssessment]:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        return (
            db.query(models.NutritionAssessment)
            .filter(
                models.NutritionAssessment.patient_id == patient_id,
                models.NutritionAssessment.clinic_id == clinic_id,
                models.NutritionAssessment.deleted_at.is_(None),
            )
            .order_by(models.NutritionAssessment.recorded_at.desc())
            .all()
        )

    @staticmethod
    def record_assessment(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        actor: User,
        weight_kg: Optional[float] = None,
        height_cm: Optional[float] = None,
        muac_cm: Optional[float] = None,
        age_months: Optional[int] = None,
        consultation_id: Optional[int] = None,
        notes: Optional[str] = None,
        nutritional_diagnosis: Optional[str] = None,
        is_follow_up: bool = False,
        follow_up_date: Optional[date] = None,
    ) -> models.NutritionAssessment:
        assert_patient_in_clinic(db, patient_id=patient_id, clinic_id=clinic_id)
        status_label = _classify_muac(muac_cm)
        row = models.NutritionAssessment(
            clinic_id=clinic_id,
            patient_id=patient_id,
            consultation_id=consultation_id,
            age_months=age_months,
            weight_kg=weight_kg,
            height_cm=height_cm,
            muac_cm=muac_cm,
            nutritional_status=status_label,
            nutritional_diagnosis=nutritional_diagnosis,
            is_follow_up=is_follow_up,
            follow_up_date=follow_up_date,
            notes=notes,
            recorded_by_user_id=actor.id,
            recorded_at=datetime.utcnow(),
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row

    @staticmethod
    def get_assessment(
        db: Session, *, clinic_id: int, assessment_id: int
    ) -> models.NutritionAssessment:
        row = (
            db.query(models.NutritionAssessment)
            .filter(
                models.NutritionAssessment.id == assessment_id,
                models.NutritionAssessment.clinic_id == clinic_id,
                models.NutritionAssessment.deleted_at.is_(None),
            )
            .first()
        )
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assessment not found")
        return row

    @staticmethod
    def dashboard_stats(db: Session, *, clinic_id: int) -> dict:
        today = date.today()
        month_start = today.replace(day=1)
        base = db.query(models.NutritionAssessment).filter(
            models.NutritionAssessment.clinic_id == clinic_id,
            models.NutritionAssessment.deleted_at.is_(None),
        )
        all_rows = base.all()
        patient_ids = {r.patient_id for r in all_rows}
        malnutrition = sum(
            1
            for r in all_rows
            if r.nutritional_status in ("moderate_malnutrition", "severe_malnutrition")
        )
        follow_ups = base.filter(models.NutritionAssessment.is_follow_up.is_(True)).count()
        month_count = base.filter(models.NutritionAssessment.recorded_at >= datetime.combine(month_start, datetime.min.time())).count()
        return {
            "children_followed": len(patient_ids),
            "malnutrition_cases": malnutrition,
            "follow_up_visits": follow_ups,
            "consultations_this_month": month_count,
        }

    @staticmethod
    def monthly_report(db: Session, *, clinic_id: int, year: int, month: int) -> dict:
        from calendar import monthrange

        start = datetime(year, month, 1)
        end = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
        rows = (
            db.query(models.NutritionAssessment)
            .filter(
                models.NutritionAssessment.clinic_id == clinic_id,
                models.NutritionAssessment.deleted_at.is_(None),
                models.NutritionAssessment.recorded_at >= start,
                models.NutritionAssessment.recorded_at <= end,
            )
            .all()
        )
        by_status: dict[str, int] = {}
        for row in rows:
            key = row.nutritional_status or "unknown"
            by_status[key] = by_status.get(key, 0) + 1
        malnutrition = sum(
            1
            for r in rows
            if r.nutritional_status in ("moderate_malnutrition", "severe_malnutrition")
        )
        follow_ups = sum(1 for r in rows if r.is_follow_up)
        return {
            "year": year,
            "month": month,
            "total_consultations": len(rows),
            "malnutrition_cases": malnutrition,
            "follow_up_visits": follow_ups,
            "by_status": by_status,
        }
