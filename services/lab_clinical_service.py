"""Laboratory dashboard, register, walk-in requests, and monthly reporting."""

from __future__ import annotations

from calendar import monthrange
from datetime import date, datetime, time

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

import models
from data.aasma_lab_catalog import (
    AASMA_CLINIC_ID,
    AASMA_EXAM_COUNT,
    AASMA_LAB_CATALOG,
    AASMA_LAB_CATEGORIES,
)
from data.lab_test_catalog import LAB_CATEGORIES, LAB_TEST_CATALOG
from models.user import User
from schemas.clinical import WalkInLabRequestCreate
from services.clinic_billing_service import ClinicBillingService, DEFAULT_LAB_FEE_GNF
from services.clinical_register_utils import patient_snapshot


class LabClinicalService:
    @staticmethod
    def sync_aasma_catalog(db: Session, *, clinic_id: int) -> None:
        if clinic_id != AASMA_CLINIC_ID:
            return
        existing = {
            row.code: row
            for row in db.query(models.ClinicLabTest).filter(models.ClinicLabTest.clinic_id == clinic_id).all()
        }
        expected_codes = {item["code"] for item in AASMA_LAB_CATALOG}
        now = datetime.utcnow()
        for item in AASMA_LAB_CATALOG:
            row = existing.get(item["code"])
            if row:
                row.name = item["name"]
                row.category = item["category"]
                row.category_label = item["category_label"]
                row.sort_order = item["sort_order"]
                row.active = True
                if item.get("price_gnf") is not None:
                    row.price_gnf = item["price_gnf"]
                row.updated_at = now
            else:
                db.add(
                    models.ClinicLabTest(
                        clinic_id=clinic_id,
                        code=item["code"],
                        name=item["name"],
                        category=item["category"],
                        category_label=item["category_label"],
                        price_gnf=item.get("price_gnf"),
                        sort_order=item["sort_order"],
                        active=True,
                        created_at=now,
                        updated_at=now,
                    )
                )
        for code, row in existing.items():
            if code not in expected_codes:
                row.active = False
                row.updated_at = now
        db.commit()

    @staticmethod
    def _serialize_clinic_test(row: models.ClinicLabTest) -> dict:
        return {
            "code": row.code,
            "name": row.name,
            "category": row.category,
            "category_label": row.category_label,
            "price_gnf": row.price_gnf,
            "sort_order": row.sort_order,
        }

    @staticmethod
    def catalog_payload(db: Session, *, clinic_id: int) -> dict:
        if clinic_id == AASMA_CLINIC_ID:
            LabClinicalService.sync_aasma_catalog(db, clinic_id=clinic_id)
            rows = (
                db.query(models.ClinicLabTest)
                .filter(
                    models.ClinicLabTest.clinic_id == clinic_id,
                    models.ClinicLabTest.active.is_(True),
                )
                .order_by(models.ClinicLabTest.sort_order.asc())
                .all()
            )
            by_label: dict[str, dict] = {}
            for row in rows:
                bucket = by_label.setdefault(
                    row.category_label,
                    {
                        "key": row.category,
                        "label": row.category_label,
                        "tests": [],
                    },
                )
                bucket["tests"].append(LabClinicalService._serialize_clinic_test(row))
            categories = list(by_label.values())
            tests = [LabClinicalService._serialize_clinic_test(row) for row in rows]
            return {
                "clinic_id": clinic_id,
                "source": "aasma_forms",
                "total_categories": len(categories),
                "total_tests": len(tests),
                "expected_categories": len(AASMA_LAB_CATEGORIES),
                "expected_tests": AASMA_EXAM_COUNT,
                "categories": categories,
                "tests": tests,
            }

        tests = [
            {**t, "price_gnf": DEFAULT_LAB_FEE_GNF, "category_label": LAB_CATEGORIES.get(t["category"], t["category"])}
            for t in LAB_TEST_CATALOG
        ]
        return {
            "clinic_id": clinic_id,
            "source": "default",
            "total_categories": len(LAB_CATEGORIES),
            "total_tests": len(tests),
            "categories": [],
            "tests": tests,
        }

    @staticmethod
    def test_catalog(*, clinic_id: int | None = None, db: Session | None = None) -> list[dict]:
        if clinic_id == AASMA_CLINIC_ID and db is not None:
            return LabClinicalService.catalog_payload(db, clinic_id=clinic_id)["tests"]
        if clinic_id == AASMA_CLINIC_ID:
            return [{**t, "price_gnf": None} for t in AASMA_LAB_CATALOG]
        return [
            {**t, "price_gnf": DEFAULT_LAB_FEE_GNF}
            for t in LAB_TEST_CATALOG
        ]

    @staticmethod
    def update_catalog_prices(
        db: Session,
        *,
        clinic_id: int,
        items: list[dict],
    ) -> dict:
        if clinic_id != AASMA_CLINIC_ID:
            raise HTTPException(status_code=400, detail="Catalogue tarifaire modifiable uniquement pour AASMA")
        LabClinicalService.sync_aasma_catalog(db, clinic_id=clinic_id)
        codes = {item["code"] for item in items}
        rows = (
            db.query(models.ClinicLabTest)
            .filter(
                models.ClinicLabTest.clinic_id == clinic_id,
                models.ClinicLabTest.code.in_(codes),
            )
            .all()
        )
        row_map = {row.code: row for row in rows}
        updated = 0
        now = datetime.utcnow()
        for item in items:
            row = row_map.get(item["code"])
            if not row:
                continue
            price = item.get("price_gnf")
            row.price_gnf = price if price is None or price >= 0 else None
            row.updated_at = now
            updated += 1
        db.commit()
        return LabClinicalService.catalog_payload(db, clinic_id=clinic_id)

    @staticmethod
    def price_for_test(*, clinic_id: int, test_code: str, db: Session | None = None) -> int | None:
        if clinic_id == AASMA_CLINIC_ID and db is not None:
            row = (
                db.query(models.ClinicLabTest)
                .filter(
                    models.ClinicLabTest.clinic_id == clinic_id,
                    models.ClinicLabTest.code == test_code,
                    models.ClinicLabTest.active.is_(True),
                )
                .first()
            )
            if row:
                return row.price_gnf
        return DEFAULT_LAB_FEE_GNF if clinic_id != AASMA_CLINIC_ID else None

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
        doctor = LabClinicalService._default_doctor(db, clinic_id)
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
            chief_complaint="Demande laboratoire directe",
            started_at=now,
        )
        db.add(consultation)
        db.flush()
        return consultation, doctor

    @staticmethod
    def create_walk_in_orders(
        db: Session,
        *,
        clinic_id: int,
        payload: WalkInLabRequestCreate,
        actor: User,
    ) -> list[models.LabOrder]:
        consultation, doctor = LabClinicalService._ensure_walk_in_consultation(
            db, clinic_id=clinic_id, patient_id=payload.patient_id
        )
        created: list[models.LabOrder] = []
        mark_paid = payload.payment_status == "paid"
        for item in payload.tests:
            price = item.price_gnf
            if price is None:
                price = LabClinicalService.price_for_test(
                    clinic_id=clinic_id, test_code=item.test_code, db=db
                )
            order = models.LabOrder(
                clinic_id=clinic_id,
                consultation_id=consultation.id,
                patient_id=payload.patient_id,
                ordered_by_user_id=actor.id,
                doctor_id=doctor.id,
                test_code=item.test_code.strip(),
                test_name=item.test_name.strip(),
                priority=payload.priority,
                clinical_notes=payload.clinical_notes,
                status="ordered",
            )
            db.add(order)
            db.flush()
            charge = ClinicBillingService.create_lab_charge(
                db,
                clinic_id=clinic_id,
                patient_id=payload.patient_id,
                lab_order_id=order.id,
                test_name=order.test_name,
                amount_gnf=price or 0,
            )
            if mark_paid:
                charge.payment_status = "paid"
                charge.payment_method = "cash"
                charge.recorded_by_user_id = actor.id
                charge.paid_at = datetime.utcnow()
            created.append(order)
        db.commit()
        for order in created:
            db.refresh(order)
        return created

    @staticmethod
    def _charge_for_order(db: Session, order: models.LabOrder) -> models.ClinicCharge | None:
        return (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == order.clinic_id,
                models.ClinicCharge.source_type == "lab_order",
                models.ClinicCharge.source_id == order.id,
            )
            .first()
        )

    @staticmethod
    def _technician_name(db: Session, result: models.LabResult | None) -> str | None:
        if not result:
            return None
        user_id = result.validated_by_user_id or result.recorded_by_user_id
        if not user_id:
            return None
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            return None
        return user.email.split("@")[0] if user.email else None

    @staticmethod
    def serialize_order(db: Session, order: models.LabOrder) -> dict:
        patient = order.patient
        charge = LabClinicalService._charge_for_order(db, order)
        result = (
            db.query(models.LabResult)
            .filter(models.LabResult.lab_order_id == order.id)
            .first()
        )
        technician = LabClinicalService._technician_name(db, result)
        return {
            "id": order.id,
            "clinic_id": order.clinic_id,
            "consultation_id": order.consultation_id,
            "patient_id": order.patient_id,
            "test_code": order.test_code,
            "test_name": order.test_name,
            "priority": order.priority,
            "status": order.status,
            "patient_name": f"{patient.first_name} {patient.last_name}" if patient else None,
            "patient_first_name": patient.first_name if patient else None,
            "patient_last_name": patient.last_name if patient else None,
            "patient_age": patient.age if patient else None,
            "patient_gender": patient.gender if patient else None,
            "patient_profession": getattr(patient, "profession", None) if patient else None,
            "patient_quartier": getattr(patient, "quartier", None) or (patient.address if patient else None),
            "patient_phone": patient.phone if patient else None,
            "price_gnf": charge.amount_gnf if charge else None,
            "payment_status": charge.payment_status if charge else None,
            "result_status": result.status if result else None,
            "validated_at": result.validated_at if result else None,
            "technician_name": technician,
            "created_at": order.created_at,
        }

    @staticmethod
    def _month_bounds(year: int, month: int) -> tuple[datetime, datetime]:
        start = datetime(year, month, 1)
        end = datetime(year, month, monthrange(year, month)[1], 23, 59, 59)
        return start, end

    @staticmethod
    def dashboard_stats(db: Session, *, clinic_id: int) -> dict:
        today_start = datetime.combine(date.today(), time.min)
        base = db.query(models.LabOrder).filter(
            models.LabOrder.clinic_id == clinic_id,
            models.LabOrder.deleted_at.is_(None),
        )
        pending = base.filter(models.LabOrder.status == "ordered").count()
        in_sampling = base.filter(models.LabOrder.status == "sample_collected").count()
        in_analysis = base.filter(models.LabOrder.status == "in_analysis").count()
        validated_today = (
            db.query(models.LabResult)
            .join(models.LabOrder)
            .filter(
                models.LabOrder.clinic_id == clinic_id,
                models.LabResult.status == "validated",
                models.LabResult.validated_at >= today_start,
            )
            .count()
        )
        today_orders = base.filter(models.LabOrder.created_at >= today_start).count()
        month_start = datetime(date.today().year, date.today().month, 1)
        month_orders = base.filter(models.LabOrder.created_at >= month_start).count()
        paid_today = (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.charge_type == "laboratory",
                models.ClinicCharge.payment_status == "paid",
                models.ClinicCharge.paid_at >= today_start,
            )
            .all()
        )
        daily_revenue_gnf = sum(c.amount_gnf for c in paid_today)
        month_paid = (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.charge_type == "laboratory",
                models.ClinicCharge.payment_status == "paid",
                models.ClinicCharge.paid_at >= month_start,
            )
            .all()
        )
        monthly_revenue_gnf = sum(c.amount_gnf for c in month_paid)
        return {
            "pending_exams": pending,
            "in_sampling": in_sampling,
            "in_analysis": in_analysis,
            "validated_today": validated_today,
            "pending_results": pending + in_sampling + in_analysis,
            "tests_today": today_orders,
            "tests_this_month": month_orders,
            "daily_revenue_gnf": daily_revenue_gnf,
            "monthly_revenue_gnf": monthly_revenue_gnf,
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
        total_revenue = 0
        for o in orders:
            by_type[o.test_name] = by_type.get(o.test_name, 0) + 1
            if o.status == "completed":
                completed += 1
            else:
                pending += 1
            charge = LabClinicalService._charge_for_order(db, o)
            if charge and charge.payment_status == "paid":
                total_revenue += charge.amount_gnf
        register_entries = []
        for idx, order in enumerate(orders, start=1):
            if not order.patient:
                continue
            result_summary = None
            validated_at = None
            for res in order.results or []:
                if res.status == "validated":
                    result_summary = res.result_summary
                    validated_at = res.validated_at
                    break
            charge = LabClinicalService._charge_for_order(db, order)
            snap_date = order.created_at.date() if order.created_at else date.today()
            register_entries.append(
                {
                    "line_number": idx,
                    "order_id": order.id,
                    "test_code": order.test_code,
                    "test_name": order.test_name,
                    "status": order.status,
                    "priority": order.priority,
                    "price_gnf": charge.amount_gnf if charge else None,
                    "payment_status": charge.payment_status if charge else None,
                    "created_at": order.created_at.isoformat() if order.created_at else None,
                    "validated_at": validated_at.isoformat() if validated_at else None,
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
            "total_revenue_gnf": total_revenue,
            "by_test_type": by_type,
            "by_category": LabClinicalService._by_category(orders, clinic_id, db),
            "register_entries": register_entries,
        }

    @staticmethod
    def _by_category(orders: list[models.LabOrder], clinic_id: int, db: Session) -> dict[str, int]:
        catalog = LabClinicalService.test_catalog(clinic_id=clinic_id, db=db)
        code_map = {t["code"]: t.get("category_label") or t.get("category") for t in catalog}
        counts: dict[str, int] = {}
        for o in orders:
            cat = code_map.get(o.test_code, "other")
            label = cat if isinstance(cat, str) and cat.isupper() else LAB_CATEGORIES.get(cat, cat)
            counts[label] = counts.get(label, 0) + 1
        return counts
