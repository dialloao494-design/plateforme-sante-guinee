"""Doctor office medicine deliveries — separate from pharmacy stock."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

import models
from models.user import User
from schemas.clinical import DoctorMedicineDeliveryCreate


class DoctorMedicineDeliveryService:
    @staticmethod
    def list_deliveries(db: Session, *, clinic_id: int, limit: int = 200) -> list[models.DoctorMedicineDelivery]:
        return (
            db.query(models.DoctorMedicineDelivery)
            .filter(
                models.DoctorMedicineDelivery.clinic_id == clinic_id,
                models.DoctorMedicineDelivery.deleted_at.is_(None),
            )
            .order_by(models.DoctorMedicineDelivery.delivered_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def create_delivery(
        db: Session,
        *,
        clinic_id: int,
        payload: DoctorMedicineDeliveryCreate,
        actor: User,
    ) -> models.DoctorMedicineDelivery:
        delivered_at = payload.delivered_at or datetime.utcnow()
        row = models.DoctorMedicineDelivery(
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            patient_name=payload.patient_name.strip(),
            medicine_name=payload.medicine_name.strip(),
            quantity=payload.quantity,
            doctor_name=payload.doctor_name.strip(),
            reason=(payload.reason or "").strip() or None,
            source="doctor_office",
            delivered_at=delivered_at,
            recorded_by_user_id=actor.id,
        )
        db.add(row)
        db.commit()
        db.refresh(row)
        return row
