"""Pharmacy dashboard, dispensing register, and monthly reporting."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

import models
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
