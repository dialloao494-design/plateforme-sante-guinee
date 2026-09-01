"""Pharmacy dashboard, dispensing register, and monthly reporting."""

from __future__ import annotations

import json
from calendar import monthrange
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session, joinedload

import models
from models.user import User
from schemas.pharmacy_his import PharmacyChargePaymentCreate, PharmacyChargePaymentLegacyCreate, PharmacyServiceRequestCreate
from services.clinic_billing_service import ClinicBillingService
from services.clinical_register_utils import patient_snapshot
from services.pharmacy_inventory_service import PharmacyInventoryService


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
        medicine_totals: dict[str, dict] = {}
        for idx, row in enumerate(rows, start=1):
            if not row.patient:
                continue
            disp_date = row.dispensed_at.date() if row.dispensed_at else date.today()
            lines = PharmacyClinicalService._line_items_from_order(row)
            for line in lines:
                name = str(line.get("product_name") or "Médicament").strip()
                bucket = medicine_totals.setdefault(name, {"medication_name": name, "quantity": 0, "revenue_gnf": 0})
                bucket["quantity"] += int(line.get("quantity") or 0)
                bucket["revenue_gnf"] += int(line.get("total_gnf") or 0)
            register_rows.append(
                {
                    "line_number": idx,
                    "order_id": row.id,
                    "patient_id": row.patient_id,
                    "patient": patient_snapshot(row.patient, disp_date),
                    "medications": PharmacyClinicalService._medications_text(row),
                    "dispensed_at": row.dispensed_at.isoformat() if row.dispensed_at else None,
                    "status": row.status,
                    "request_number": PharmacyClinicalService.request_number(row),
                }
            )
        charges = db.query(models.ClinicCharge).filter(
            models.ClinicCharge.clinic_id == clinic_id,
            models.ClinicCharge.charge_type == "pharmacy",
            models.ClinicCharge.created_at >= start,
            models.ClinicCharge.created_at <= end,
        ).all()
        generated = sum(int(c.amount_gnf or 0) for c in charges)
        payment_rows = (
            db.query(models.ClinicChargePayment)
            .join(models.ClinicCharge, models.ClinicCharge.id == models.ClinicChargePayment.charge_id)
            .filter(
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.charge_type == "pharmacy",
                models.ClinicChargePayment.created_at >= start,
                models.ClinicChargePayment.created_at <= end,
            )
            .all()
        )
        collected = sum(int(payment.amount_gnf or 0) for payment in payment_rows)
        # Older single-payment records predate split payment rows.
        payment_charge_ids = {payment.charge_id for payment in payment_rows}
        legacy_paid = db.query(models.ClinicCharge).filter(
            models.ClinicCharge.clinic_id == clinic_id,
            models.ClinicCharge.charge_type == "pharmacy",
            models.ClinicCharge.payment_status == "paid",
            models.ClinicCharge.paid_at >= start,
            models.ClinicCharge.paid_at <= end,
        ).all()
        collected += sum(int(charge.paid_amount_gnf or charge.amount_gnf or 0) for charge in legacy_paid if charge.id not in payment_charge_ids)
        pending = sum(max(0, int(c.amount_gnf or 0) - int(c.paid_amount_gnf or 0)) for c in charges)
        collected_for_period_sales = sum(min(int(c.amount_gnf or 0), int(c.paid_amount_gnf or 0)) for c in charges)
        unique_patients = len({charge.patient_id for charge in charges if charge.patient_id})
        return {
            "year": year,
            "month": month,
            "clinic_id": clinic_id,
            "total_dispensed": len(rows),
            "unique_patients": unique_patients,
            "requests_created": len(charges),
            "generated_revenue_gnf": generated,
            "collected_revenue_gnf": collected,
            "pending_revenue_gnf": pending,
            "collection_rate_percent": round((collected_for_period_sales / generated * 100), 1) if generated else 0,
            "top_medications": sorted(
                medicine_totals.values(), key=lambda item: (item["quantity"], item["revenue_gnf"]), reverse=True
            )[:10],
            "register_rows": register_rows,
        }

    @staticmethod
    def request_number(order: models.PharmacyOrder) -> str:
        return f"PHARM-{int(order.clinic_id):03d}-{int(order.id):06d}"

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
            raise HTTPException(
                status_code=400,
                detail="Aucun médecin configuré pour cette clinique",
            )
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
    def _payment_rows(charge: models.ClinicCharge) -> list[dict]:
        return [
            {
                "id": p.id,
                "amount_gnf": p.amount_gnf,
                "payment_method": p.payment_method,
                "reference": p.reference,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in sorted(charge.payments or [], key=lambda x: x.created_at or datetime.min)
        ]

    @staticmethod
    def serialize_service_request(db: Session, order: models.PharmacyOrder) -> dict:
        charge = PharmacyClinicalService._charge_for_order(db, order)
        lines = PharmacyClinicalService._line_items_from_order(order)
        subtotal = int(charge.subtotal_amount_gnf or charge.amount_gnf) if charge else sum(
            int(l.get("total_gnf") or 0) for l in lines
        )
        exemption_percent = float(charge.exemption_percent or 0) if charge else 0
        exemption_amount = int(charge.exemption_amount_gnf or 0) if charge else 0
        total = int(charge.amount_gnf) if charge else subtotal
        paid = int(charge.paid_amount_gnf or 0) if charge else 0
        if charge and charge.payment_status == "paid" and paid == 0:
            paid = total
        payments = PharmacyClinicalService._payment_rows(charge) if charge else []
        primary_method = charge.payment_method if charge else None
        if not primary_method and payments:
            primary_method = payments[-1]["payment_method"]
        return {
            "order_id": order.id,
            "charge_id": charge.id if charge else None,
            "patient_id": order.patient_id,
            "subtotal_gnf": subtotal,
            "exemption_percent": exemption_percent,
            "exemption_amount_gnf": exemption_amount,
            "total_gnf": total,
            "paid_amount_gnf": paid,
            "remaining_gnf": max(0, total - paid),
            "payment_status": charge.payment_status if charge else "pending",
            "payment_method": primary_method,
            "payments": payments,
            "items": lines,
            "request_number": PharmacyClinicalService.request_number(order),
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
                    "inventory_item_id": item.inventory_item_id,
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
    def _finalize_dispense(
        db: Session,
        *,
        clinic_id: int,
        charge: models.ClinicCharge,
        actor: User,
    ) -> models.PharmacyOrder | None:
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
            lines = PharmacyClinicalService._line_items_from_order(order)
            PharmacyInventoryService.deduct_for_lines(db, clinic_id=clinic_id, lines=lines)
        return order

    @staticmethod
    def add_charge_payment(
        db: Session,
        *,
        clinic_id: int,
        charge_id: int,
        payload: PharmacyChargePaymentCreate,
        actor: User,
    ) -> dict:
        charge = (
            db.query(models.ClinicCharge)
            .options(joinedload(models.ClinicCharge.payments))
            .filter(
                models.ClinicCharge.id == charge_id,
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.charge_type == "pharmacy",
            )
            .first()
        )
        if not charge:
            raise HTTPException(status_code=404, detail="Facture pharmacie introuvable")
        if charge.payment_status == "paid":
            raise HTTPException(status_code=400, detail="Facture déjà soldée")

        subtotal = int(charge.subtotal_amount_gnf or charge.amount_gnf)
        if payload.exemption_percent is not None and not charge.payments:
            exemption_percent = float(payload.exemption_percent)
            exemption_amount = int(subtotal * exemption_percent / 100)
            charge.exemption_percent = int(round(exemption_percent))
            charge.exemption_amount_gnf = exemption_amount
            charge.amount_gnf = max(0, subtotal - exemption_amount)
            db.flush()

        net_total = int(charge.amount_gnf)
        paid_so_far = int(charge.paid_amount_gnf or 0)
        remaining = max(0, net_total - paid_so_far)
        if remaining <= 0:
            raise HTTPException(status_code=400, detail="Facture déjà soldée")
        if payload.amount_gnf > remaining:
            raise HTTPException(
                status_code=400,
                detail=f"Montant supérieur au reste à payer ({remaining} GNF)",
            )

        payment = models.ClinicChargePayment(
            charge_id=charge.id,
            amount_gnf=int(payload.amount_gnf),
            payment_method=payload.payment_method,
            reference=payload.reference,
            recorded_by_user_id=actor.id,
        )
        db.add(payment)
        charge.paid_amount_gnf = paid_so_far + int(payload.amount_gnf)
        charge.payment_method = payload.payment_method
        charge.recorded_by_user_id = actor.id
        remaining_after = max(0, net_total - charge.paid_amount_gnf)
        if remaining_after <= 0:
            charge.payment_status = "paid"
            charge.paid_at = datetime.utcnow()
            db.flush()
            PharmacyClinicalService._finalize_dispense(
                db, clinic_id=clinic_id, charge=charge, actor=actor
            )
        db.commit()
        charge = (
            db.query(models.ClinicCharge)
            .options(joinedload(models.ClinicCharge.payments))
            .filter(models.ClinicCharge.id == charge.id)
            .first()
        )
        order = (
            db.query(models.PharmacyOrder)
            .filter(
                models.PharmacyOrder.clinic_id == clinic_id,
                models.PharmacyOrder.id == charge.source_id,
            )
            .first()
        )
        if not order:
            return {
                "order_id": charge.source_id,
                "charge_id": charge.id,
                "patient_id": charge.patient_id,
                "subtotal_gnf": subtotal,
                "exemption_percent": float(charge.exemption_percent or 0),
                "exemption_amount_gnf": int(charge.exemption_amount_gnf or 0),
                "total_gnf": charge.amount_gnf,
                "paid_amount_gnf": charge.paid_amount_gnf,
                "remaining_gnf": max(0, charge.amount_gnf - charge.paid_amount_gnf),
                "payment_status": charge.payment_status,
                "payment_method": charge.payment_method,
                "payments": PharmacyClinicalService._payment_rows(charge),
                "items": [],
                "request_number": f"PHARM-{int(clinic_id):03d}-{int(charge.source_id):06d}",
            }
        db.refresh(order)
        return PharmacyClinicalService.serialize_service_request(db, order)

    @staticmethod
    def pay_service_charge(
        db: Session,
        *,
        clinic_id: int,
        charge_id: int,
        payload: PharmacyChargePaymentLegacyCreate,
        actor: User,
    ) -> dict:
        """Legacy single-shot payment — delegates to add_charge_payment."""
        subtotal_charge = (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.id == charge_id,
                models.ClinicCharge.clinic_id == clinic_id,
            )
            .first()
        )
        if not subtotal_charge:
            raise HTTPException(status_code=404, detail="Facture pharmacie introuvable")
        subtotal = int(subtotal_charge.subtotal_amount_gnf or subtotal_charge.amount_gnf)
        exemption_percent = float(payload.exemption_percent or 0)
        net_total = max(0, subtotal - int(subtotal * exemption_percent / 100))
        if payload.amount_received_gnf < net_total:
            raise HTTPException(
                status_code=400,
                detail="Montant reçu insuffisant pour finaliser le paiement",
            )
        return PharmacyClinicalService.add_charge_payment(
            db,
            clinic_id=clinic_id,
            charge_id=charge_id,
            payload=PharmacyChargePaymentCreate(
                payment_method=payload.payment_method,
                amount_gnf=net_total,
                exemption_percent=exemption_percent,
            ),
            actor=actor,
        )
