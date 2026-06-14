"""Clinical and financial reporting for clinic management."""

from __future__ import annotations

import csv
import io
from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

import models


class ClinicalReportingService:
    @staticmethod
    def _day_bounds(day: date) -> tuple[datetime, datetime]:
        return datetime.combine(day, time.min), datetime.combine(day, time.max)

    @staticmethod
    def period_summary(
        db: Session, *, clinic_id: int, start: date, end: date
    ) -> dict:
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)

        appointments = (
            db.query(models.RendezVous)
            .filter(
                models.RendezVous.clinic_id == clinic_id,
                models.RendezVous.date >= start_dt,
                models.RendezVous.date <= end_dt,
            )
            .all()
        )
        consultations = (
            db.query(models.ClinicalConsultation)
            .filter(
                models.ClinicalConsultation.clinic_id == clinic_id,
                models.ClinicalConsultation.created_at >= start_dt,
                models.ClinicalConsultation.created_at <= end_dt,
            )
            .count()
        )
        lab_orders = (
            db.query(models.LabOrder)
            .filter(models.LabOrder.clinic_id == clinic_id, models.LabOrder.created_at >= start_dt)
            .filter(models.LabOrder.created_at <= end_dt)
            .count()
        )
        imaging_orders = (
            db.query(models.ImagingOrder)
            .filter(models.ImagingOrder.clinic_id == clinic_id, models.ImagingOrder.created_at >= start_dt)
            .filter(models.ImagingOrder.created_at <= end_dt)
            .count()
        )
        pharmacy_dispensed = (
            db.query(models.PharmacyOrder)
            .filter(
                models.PharmacyOrder.clinic_id == clinic_id,
                models.PharmacyOrder.status == "dispensed",
                models.PharmacyOrder.dispensed_at >= start_dt,
                models.PharmacyOrder.dispensed_at <= end_dt,
            )
            .count()
        )
        admissions = (
            db.query(models.Admission)
            .filter(
                models.Admission.clinic_id == clinic_id,
                models.Admission.created_at >= start_dt,
                models.Admission.created_at <= end_dt,
            )
            .count()
        )
        discharges = (
            db.query(models.DischargeSummary)
            .filter(
                models.DischargeSummary.clinic_id == clinic_id,
                models.DischargeSummary.discharged_at >= start_dt,
                models.DischargeSummary.discharged_at <= end_dt,
            )
            .count()
        )

        revenue = ClinicalReportingService.revenue_summary(db, clinic_id=clinic_id, start=start, end=end)

        return {
            "period_start": start.isoformat(),
            "period_end": end.isoformat(),
            "appointments_total": len(appointments),
            "appointments_completed": sum(1 for a in appointments if a.clinical_status == "completed"),
            "appointments_cancelled": sum(1 for a in appointments if a.status == "cancelled"),
            "consultations": consultations,
            "lab_orders": lab_orders,
            "imaging_orders": imaging_orders,
            "pharmacy_dispensed": pharmacy_dispensed,
            "admissions": admissions,
            "discharges": discharges,
            "revenue": revenue,
        }

    @staticmethod
    def revenue_summary(
        db: Session, *, clinic_id: int, start: date, end: date
    ) -> dict:
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)

        paid_charges = (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.payment_status == "paid",
                models.ClinicCharge.paid_at >= start_dt,
                models.ClinicCharge.paid_at <= end_dt,
            )
            .all()
        )
        paid_invoices = (
            db.query(models.Invoice)
            .filter(
                models.Invoice.clinic_id == clinic_id,
                models.Invoice.status == "paid",
                models.Invoice.paid_at >= start_dt,
                models.Invoice.paid_at <= end_dt,
            )
            .all()
        )
        pending_charges = (
            db.query(models.ClinicCharge)
            .filter(
                models.ClinicCharge.clinic_id == clinic_id,
                models.ClinicCharge.payment_status == "pending",
            )
            .count()
        )

        by_type: dict[str, int] = {}
        for c in paid_charges:
            by_type[c.charge_type] = by_type.get(c.charge_type, 0) + (c.amount_gnf or 0)

        charge_total = sum(c.amount_gnf or 0 for c in paid_charges)
        invoice_total = sum(i.paid_amount_gnf or 0 for i in paid_invoices)

        return {
            "charges_collected_gnf": charge_total,
            "invoices_paid_gnf": invoice_total,
            "total_collected_gnf": charge_total + invoice_total,
            "pending_charges_count": pending_charges,
            "by_charge_type": by_type,
            "paid_invoices_count": len(paid_invoices),
        }

    @staticmethod
    def export_csv(db: Session, *, clinic_id: int, start: date, end: date) -> str:
        summary = ClinicalReportingService.period_summary(
            db, clinic_id=clinic_id, start=start, end=end
        )
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["Rapport clinique", summary["period_start"], "→", summary["period_end"]])
        writer.writerow([])
        writer.writerow(["Indicateur", "Valeur"])
        for key in (
            "appointments_total",
            "appointments_completed",
            "appointments_cancelled",
            "consultations",
            "lab_orders",
            "imaging_orders",
            "pharmacy_dispensed",
            "admissions",
            "discharges",
        ):
            writer.writerow([key, summary[key]])
        writer.writerow([])
        writer.writerow(["Revenus"])
        for k, v in summary["revenue"].items():
            if isinstance(v, dict):
                writer.writerow([k, ""])
                for sk, sv in v.items():
                    writer.writerow([f"  {sk}", sv])
            else:
                writer.writerow([k, v])
        return buf.getvalue()

    @staticmethod
    def default_period() -> tuple[date, date]:
        end = date.today()
        start = end - timedelta(days=30)
        return start, end
