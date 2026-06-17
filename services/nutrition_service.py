"""Nutrition assessment service — child growth monitoring."""

from __future__ import annotations

from datetime import datetime
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
