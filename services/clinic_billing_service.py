"""In-clinic billing — consultation, laboratory, pharmacy charges."""

from __future__ import annotations

from datetime import date, datetime, time

from fastapi import HTTPException
from sqlalchemy.orm import Session

import models
from models.user import User

DEFAULT_LAB_FEE_GNF = 75_000
DEFAULT_PHARMACY_ITEM_FEE_GNF = 25_000


class ClinicBillingService:
    @staticmethod
    def _existing_charge(
        db: Session, *, clinic_id: int, source_type: str, source_id: int
    ) -> models.ClinicCharge | None:
        return (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.source_type == source_type,
                models.ClinicCharge.source_id == source_id,
            )
            .first()
        )

    @staticmethod
    def create_consultation_charge(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        appointment_id: int,
        amount_gnf: int,
        description: str,
    ) -> models.ClinicCharge:
        existing = ClinicBillingService._existing_charge(
            db, clinic_id=clinic_id, source_type="appointment", source_id=appointment_id
        )
        if existing:
            return existing
        charge = models.ClinicCharge(
            clinic_id=clinic_id,
            patient_id=patient_id,
            charge_type="consultation",
            source_type="appointment",
            source_id=appointment_id,
            description=description,
            amount_gnf=amount_gnf,
            payment_status="pending",
        )
        db.add(charge)
        db.commit()
        db.refresh(charge)
        return charge

    @staticmethod
    def create_lab_charge(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        lab_order_id: int,
        test_name: str,
        amount_gnf: int = DEFAULT_LAB_FEE_GNF,
    ) -> models.ClinicCharge:
        existing = ClinicBillingService._existing_charge(
            db, clinic_id=clinic_id, source_type="lab_order", source_id=lab_order_id
        )
        if existing:
            return existing
        charge = models.ClinicCharge(
            clinic_id=clinic_id,
            patient_id=patient_id,
            charge_type="laboratory",
            source_type="lab_order",
            source_id=lab_order_id,
            description=f"Examen laboratoire — {test_name}",
            amount_gnf=amount_gnf,
            payment_status="pending",
        )
        db.add(charge)
        db.commit()
        db.refresh(charge)
        return charge

    @staticmethod
    def create_pharmacy_charge(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
        pharmacy_order_id: int,
        medications: str,
        amount_gnf: int,
    ) -> models.ClinicCharge:
        existing = ClinicBillingService._existing_charge(
            db, clinic_id=clinic_id, source_type="pharmacy_order", source_id=pharmacy_order_id
        )
        if existing:
            return existing
        charge = models.ClinicCharge(
            clinic_id=clinic_id,
            patient_id=patient_id,
            charge_type="pharmacy",
            source_type="pharmacy_order",
            source_id=pharmacy_order_id,
            description=f"Pharmacie — {medications}",
            amount_gnf=amount_gnf,
            payment_status="pending",
        )
        db.add(charge)
        db.commit()
        db.refresh(charge)
        return charge

    @staticmethod
    def pharmacy_amount_from_items(items: list) -> int:
        total = 0
        for item in items:
            qty = item.quantity or 1
            total += DEFAULT_PHARMACY_ITEM_FEE_GNF * qty
        return max(total, DEFAULT_PHARMACY_ITEM_FEE_GNF)

    @staticmethod
    def pending_charges(db: Session, *, clinic_id: int) -> list[models.ClinicCharge]:
        return (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.payment_status == "pending",
            )
            .order_by(models.ClinicCharge.created_at.asc())
            .all()
        )

    @staticmethod
    def record_payment(
        db: Session,
        *,
        charge_id: int,
        clinic_id: int,
        user: User,
        payment_method: str,
    ) -> models.ClinicCharge:
        charge = (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.id == charge_id,
                models.ClinicCharge.clinic_id == clinic_id,
            )
            .first()
        )
        if not charge:
            raise HTTPException(status_code=404, detail="Charge not found")
        if charge.payment_status == "paid":
            raise HTTPException(status_code=400, detail="Charge already paid")

        charge.payment_status = "paid"
        charge.payment_method = payment_method
        charge.recorded_by_user_id = user.id
        charge.paid_at = datetime.utcnow()
        charge.updated_at = datetime.utcnow()

        if charge.source_type == "appointment":
            rdv = (
                db.query(models.RendezVous)
                .filter(models.RendezVous.id == charge.source_id)
                .first()
            )
            if rdv:
                rdv.payment_status = "paid"
                rdv.price = charge.amount_gnf

        db.commit()
        db.refresh(charge)
        return charge

    @staticmethod
    def daily_summary(db: Session, *, clinic_id: int, day: date | None = None) -> dict:
        target = day or date.today()
        start = datetime.combine(target, time.min)
        end = datetime.combine(target, time.max)

        paid = (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.payment_status == "paid",
                models.ClinicCharge.paid_at >= start,
                models.ClinicCharge.paid_at <= end,
            )
            .all()
        )
        pending = (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.payment_status == "pending",
            )
            .all()
        )

        by_type: dict[str, int] = {"consultation": 0, "laboratory": 0, "pharmacy": 0}
        by_method: dict[str, int] = {}
        for c in paid:
            by_type[c.charge_type] = by_type.get(c.charge_type, 0) + c.amount_gnf
            method = c.payment_method or "unknown"
            by_method[method] = by_method.get(method, 0) + c.amount_gnf

        return {
            "date": target.isoformat(),
            "total_collected_gnf": sum(c.amount_gnf for c in paid),
            "total_pending_gnf": sum(c.amount_gnf for c in pending),
            "paid_count": len(paid),
            "pending_count": len(pending),
            "by_charge_type": by_type,
            "by_payment_method": by_method,
        }
