"""Pharmacy dashboard, dispensing register, and monthly reporting."""

from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

import models
from models.user import User
from schemas.pharmacy_his import PharmacyChargePaymentCreate, PharmacyServiceRequestCreate
from services.clinic_billing_service import ClinicBillingService
from services.clinical_register_utils import patient_snapshot


class PharmacyClinicalService:
    @staticmethod
    def dashboard_stats(db: Session, *, clinic_id: int) -> dict:
        today_start = datetime.combine(date.today(), datetime.min.time())
        month_start = datetime(date.today().year, date.today().month, 1)
        inventory = (
            db.query(models.PharmacyInventoryItem)
            .filter(models.PharmacyInventoryItem.clinic_id == clinic_id)
            .all()
        )
        stock_value = sum(i.quantity * i.unit_price_gnf for i in inventory)
        low_stock = [i for i in inventory if i.quantity <= i.reorder_level]
        orders = db.query(models.PharmacyOrder).filter(
            models.PharmacyOrder.clinic_id == clinic_id,
        )
        dispensed_today = orders.filter(
            models.PharmacyOrder.status == "dispensed",
            models.PharmacyOrder.dispensed_at >= today_start,
        ).count()
        dispensed_month = orders.filter(
            models.PharmacyOrder.status == "dispensed",
            models.PharmacyOrder.dispensed_at >= month_start,
        ).count()
        pending = orders.filter(models.PharmacyOrder.status.in_(["pending", "preparing"])).count()
        return {
            "stock_value_gnf": stock_value,
            "low_stock_count": len(low_stock),
            "low_stock_items": [
                {"sku": i.sku, "name": i.medication_name, "quantity": i.quantity, "reorder_level": i.reorder_level}
                for i in low_stock[:20]
            ],
            "dispensed_today": dispensed_today,
            "dispensed_this_month": dispensed_month,
            "pending_orders": pending,
            "inventory_count": len(inventory),
        }

    @staticmethod
    def monthly_report(db: Session, *, clinic_id: int, year: int, month: int) -> dict:
        start = datetime(year, month, 1)
        end = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
        rows = (
            db.query(models.PharmacyOrder)
            .options(
                joinedload(models.PharmacyOrder.patient),
                joinedload(models.PharmacyOrder.prescription).joinedload(models.Prescription.items),
            )
            .filter(
                models.PharmacyOrder.clinic_id == clinic_id,
                models.PharmacyOrder.status == "dispensed",
                models.PharmacyOrder.dispensed_at >= start,
                models.PharmacyOrder.dispensed_at <= end,
            )
            .order_by(models.PharmacyOrder.dispensed_at)
            .all()
        )
        register_rows = []
        for idx, row in enumerate(rows, start=1):
            if not row.patient:
                continue
            disp_date = row.dispensed_at.date() if row.dispensed_at else date.today()
            register_rows.append(
                {
                    "line_number": idx,
                    "order_id": row.id,
                    "patient_id": row.patient_id,
                    "patient": patient_snapshot(row.patient, disp_date),
                    "medications": PharmacyClinicalService._medications_text(row),
                    "dispensed_at": row.dispensed_at.isoformat() if row.dispensed_at else None,
                    "status": row.status,
                }
            )
        return {
            "year": year,
            "month": month,
            "clinic_id": clinic_id,
            "total_dispensed": len(rows),
            "register_rows": register_rows,
        }

    @staticmethod
    def _medications_text(order: models.PharmacyOrder) -> str:
        if not order.prescription or not order.prescription.items:
            return order.notes or "—"
        parts = [f"{i.medication_name} {i.dosage or ''}".strip() for i in order.prescription.items]
        return "; ".join(parts) if parts else "—"

    @staticmethod
    def _default_doctor(db: Session, clinic_id: int) -> models.Doctor:
        doctor = (
            db.query(models.Doctor)
            .filter(models.Doctor.clinic_id == clinic_id)
            .order_by(models.Doctor.id.asc())
            .first()
        )
        if not doctor:
            doctor = db.query(models.Doctor).order_by(models.Doctor.id.asc()).first()
        if not doctor:
            raise HTTPException(status_code=400, detail="Aucun médecin configuré pour cette clinique")
        return doctor

    @staticmethod
    def _ensure_walk_in_consultation(
        db: Session,
        *,
        clinic_id: int,
        patient_id: int,
    ) -> tuple[models.ClinicalConsultation, models.Doctor]:
        patient = (
            db.query(models.Patient)
            .filter(models.Patient.id == patient_id, models.Patient.clinic_id == clinic_id)
            .first()
        )
        if not patient:
            raise HTTPException(status_code=404, detail="Patient introuvable dans cette clinique")
        doctor = PharmacyClinicalService._default_doctor(db, clinic_id)
        now = datetime.utcnow()
        rdv = models.RendezVous(
            date=now,
            duration_minutes=15,
            status="confirmed",
            payment_status="paid",
            price=0,
            consultation_type="physical",
            doctor_id=doctor.id,
            patient_id=patient_id,
            clinic_id=clinic_id,
            clinical_status="checked_in",
        )
        db.add(rdv)
        db.flush()
        consultation = models.ClinicalConsultation(
            clinic_id=clinic_id,
            appointment_id=rdv.id,
            patient_id=patient_id,
            doctor_id=doctor.id,
            status="in_progress",
            chief_complaint="Demande pharmacie directe",
            started_at=now,
        )
        db.add(consultation)
        db.flush()
        return consultation, doctor

    @staticmethod
    def _line_items_from_order(order: models.PharmacyOrder) -> list[dict]:
        try:
            payload = json.loads(order.notes or "")
            lines = payload.get("lines")
            if isinstance(lines, list) and lines:
                return lines
        except (TypeError, json.JSONDecodeError):
            pass
        if order.prescription and order.prescription.items:
            return [
                {
                    "product_name": item.medication_name,
                    "quantity": item.quantity or 1,
                    "unit_price_gnf": 0,
                    "total_gnf": 0,
                }
                for item in order.prescription.items
            ]
        return []

    @staticmethod
    def _charge_for_order(db: Session, order: models.PharmacyOrder) -> models.ClinicCharge | None:
        return (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == order.clinic_id,
                models.ClinicCharge.source_type == "pharmacy_order",
                models.ClinicCharge.source_id == order.id,
            )
            .first()
        )

    @staticmethod
    def serialize_service_request(db: Session, order: models.PharmacyOrder) -> dict:
        charge = PharmacyClinicalService._charge_for_order(db, order)
        lines = PharmacyClinicalService._line_items_from_order(order)
        total = charge.amount_gnf if charge else sum(int(l.get("total_gnf") or 0) for l in lines)
        paid = charge.amount_gnf if charge and charge.payment_status == "paid" else 0
        return {
            "order_id": order.id,
            "charge_id": charge.id if charge else None,
            "patient_id": order.patient_id,
            "total_gnf": total,
            "paid_amount_gnf": paid,
            "remaining_gnf": max(0, total - paid),
            "payment_status": charge.payment_status if charge else "pending",
            "payment_method": charge.payment_method if charge else None,
            "items": lines,
        }

    @staticmethod
    def create_service_request(
        db: Session,
        *,
        clinic_id: int,
        payload: PharmacyServiceRequestCreate,
        actor: User,
    ) -> dict:
        consultation, doctor = PharmacyClinicalService._ensure_walk_in_consultation(
            db, clinic_id=clinic_id, patient_id=payload.patient_id
        )
        lines = []
        total = 0
        for item in payload.items:
            line_total = int(item.quantity) * int(item.unit_price_gnf)
            total += line_total
            lines.append(
                {
                    "product_name": item.product_name.strip(),
                    "quantity": int(item.quantity),
                    "unit_price_gnf": int(item.unit_price_gnf),
                    "total_gnf": line_total,
                }
            )
        if total <= 0:
            raise HTTPException(status_code=400, detail="Le montant total doit être supérieur à zéro")

        rx = models.Prescription(
            clinic_id=clinic_id,
            consultation_id=consultation.id,
            patient_id=payload.patient_id,
            prescriber_doctor_id=doctor.id,
            status="active",
            notes=payload.notes,
        )
        db.add(rx)
        db.flush()
        for line in lines:
            db.add(
                models.PrescriptionItem(
                    prescription_id=rx.id,
                    medication_name=line["product_name"],
                    dosage=f"{line['unit_price_gnf']} GNF/u",
                    route="oral",
                    frequency="—",
                    duration_days=1,
                    quantity=line["quantity"],
                    instructions=None,
                )
            )
        order = models.PharmacyOrder(
            clinic_id=clinic_id,
            prescription_id=rx.id,
            patient_id=payload.patient_id,
            status="pending",
            notes=json.dumps({"lines": lines, "service_request": True}),
        )
        db.add(order)
        db.flush()
        meds = ", ".join(l["product_name"] for l in lines)
        ClinicBillingService.create_pharmacy_charge(
            db,
            clinic_id=clinic_id,
            patient_id=payload.patient_id,
            pharmacy_order_id=order.id,
            medications=meds,
            amount_gnf=total,
        )
        db.commit()
        db.refresh(order)
        return PharmacyClinicalService.serialize_service_request(db, order)

    @staticmethod
    def pay_service_charge(
        db: Session,
        *,
        clinic_id: int,
        charge_id: int,
        payload: PharmacyChargePaymentCreate,
        actor: User,
    ) -> dict:
        charge = (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.id == charge_id,
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.charge_type == "pharmacy",
            )
            .first()
        )
        if not charge:
            raise HTTPException(status_code=404, detail="Facture pharmacie introuvable")
        if payload.amount_received_gnf < charge.amount_gnf:
            raise HTTPException(
                status_code=400,
                detail="Montant reçu insuffisant pour finaliser le paiement",
            )
        ClinicBillingService.record_payment(
            db,
            charge_id=charge.id,
            clinic_id=clinic_id,
            user=actor,
            payment_method=payload.payment_method,
        )
        order = (
            db.query(models.PharmacyOrder)
            .filter(
                models.PharmacyOrder.clinic_id == clinic_id,
                models.PharmacyOrder.id == charge.source_id,
            )
            .first()
        )
        if order and order.status == "pending":
            order.status = "dispensed"
            order.dispensed_at = datetime.utcnow()
            order.prepared_by_user_id = actor.id
            db.commit()
            db.refresh(order)
        db.refresh(charge)
        if not order:
            return {
                "order_id": charge.source_id,
                "charge_id": charge.id,
                "patient_id": charge.patient_id,
                "total_gnf": charge.amount_gnf,
                "paid_amount_gnf": charge.amount_gnf,
                "remaining_gnf": 0,
                "payment_status": charge.payment_status,
                "payment_method": charge.payment_method,
                "items": [],
            }
        return PharmacyClinicalService.serialize_service_request(db, order)
