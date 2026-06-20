"""Laboratory dashboard, register, and monthly reporting."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

import models
from data.lab_test_catalog import LAB_CATEGORIES, LAB_TEST_CATALOG
from services.clinical_register_utils import wrap_register_rows


class LabClinicalService:
    @staticmethod
    def test_catalog() -> list[dict]:
        return LAB_TEST_CATALOG

    @staticmethod
    def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
        start = datetime(year, month, 1)
        end = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
        return start, end

    @staticmethod
    def dashboard_stats(db: Session, *, clinic_id: int) -> dict:
        today_start = datetime.combine(date.today(), datetime.min.time())
        base = db.query(models.LabOrder).filter(
            models.LabOrder.clinic_id == clinic_id,
            models.LabOrder.deleted_at.is_(None),
        )
        pending = base.filter(models.LabOrder.status.in_(["ordered", "sample_collected", "in_analysis"])).count()
        today_orders = base.filter(models.LabOrder.created_at >= today_start).count()
        month_start = datetime(date.today().year, date.today().month, 1)
        month_orders = base.filter(models.LabOrder.created_at >= month_start).all()
        by_type: dict[str, int] = {}
        for o in month_orders:
            by_type[o.test_name] = by_type.get(o.test_name, 0) + 1
        validated = (
            db.query(models.LabResult)
            .join(models.LabOrder)
            .filter(
                models.LabOrder.clinic_id == clinic_id,
                models.LabResult.status == "validated",
            )
            .count()
        )
        return {
            "pending_results": pending,
            "tests_today": today_orders,
            "tests_this_month": len(month_orders),
            "validated_total": validated,
            "by_test_type": by_type,
        }

    @staticmethod
    def list_validated_results(db: Session, *, clinic_id: int, limit: int = 100) -> list[models.LabResult]:
        return (
            db.query(models.LabResult)
            .join(models.LabOrder)
            .options(joinedload(models.LabResult.lab_order).joinedload(models.LabOrder.patient))
            .filter(
                models.LabOrder.clinic_id == clinic_id,
                models.LabResult.status == "validated",
            )
            .order_by(models.LabResult.validated_at.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def monthly_report(db: Session, *, clinic_id: int, year: int, month: int) -> dict:
        start, end = LabClinicalService._month_bounds(year, month)
        orders = (
            db.query(models.LabOrder)
            .options(joinedload(models.LabOrder.patient), joinedload(models.LabOrder.results))
            .filter(
                models.LabOrder.clinic_id == clinic_id,
                models.LabOrder.deleted_at.is_(None),
                models.LabOrder.created_at >= start,
                models.LabOrder.created_at <= end,
            )
            .order_by(models.LabOrder.created_at)
            .all()
        )
        by_type: dict[str, int] = {}
        pending = 0
        completed = 0
        for o in orders:
            by_type[o.test_name] = by_type.get(o.test_name, 0) + 1
            if o.status == "completed":
                completed += 1
            else:
                pending += 1
        register_entries = []
        for idx, order in enumerate(orders, start=1):
            if not order.patient:
                continue
            result_summary = None
            for res in order.results or []:
                if res.status == "validated":
                    result_summary = res.result_summary
                    break
            from services.clinical_register_utils import patient_snapshot

            snap_date = order.created_at.date() if order.created_at else date.today()
            register_entries.append(
                {
                    "line_number": idx,
                    "order_id": order.id,
                    "test_code": order.test_code,
                    "test_name": order.test_name,
                    "status": order.status,
                    "priority": order.priority,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "result_summary": result_summary,
                    "patient": patient_snapshot(order.patient, snap_date),
                }
            )
        return {
            "year": year,
            "month": month,
            "clinic_id": clinic_id,
            "total_tests": len(orders),
            "completed": completed,
            "pending": pending,
            "by_test_type": by_type,
            "by_category": LabClinicalService._by_category(orders),
            "register_entries": register_entries,
        }

    @staticmethod
    def _by_category(orders: list[models.LabOrder]) -> dict[str, int]:
        code_map = {t["code"]: t["category"] for t in LAB_TEST_CATALOG}
        counts: dict[str, int] = {}
        for o in orders:
            cat = code_map.get(o.test_code, "other")
            label = LAB_CATEGORIES.get(cat, cat)
            counts[label] = counts.get(label, 0) + 1
        return counts
