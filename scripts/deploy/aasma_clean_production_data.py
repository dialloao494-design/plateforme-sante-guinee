#!/usr/bin/env python3
"""Remove AASMA clinic (id=17) test/demo clinical data — keep staff accounts."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from sqlalchemy import or_

import models
from data.aasma_lab_catalog import AASMA_CLINIC_ID
from database import SessionLocal

TEST_NAME_PATTERNS = (
    r"^E2E",
    r"^Dashboard",
    r"^Test",
    r"^Demo",
    r"^Fake",
    r"^Sample",
    r"^Browser",
    r"^ClinicE2E",
)


def is_test_patient(patient: models.Patient) -> bool:
    last = (patient.last_name or "").strip()
    first = (patient.first_name or "").strip()
    for pat in TEST_NAME_PATTERNS:
        if re.search(pat, last, re.I):
            return True
    if last.upper().startswith("E2E") or first.upper() == "CLINIC" and last.upper().startswith("E2E"):
        return True
    return False


def purge_patient(db, patient_id: int) -> dict[str, int]:
    counts: dict[str, int] = {}

    def _delete(model, label: str, *filters):
        n = db.query(model).filter(*filters).delete(synchronize_session=False)
        counts[label] = counts.get(label, 0) + n

    lab_order_ids = [
        row[0]
        for row in db.query(models.LabOrder.id).filter(models.LabOrder.patient_id == patient_id).all()
    ]
    if lab_order_ids:
        _delete(models.LabResult, "lab_results", models.LabResult.lab_order_id.in_(lab_order_ids))
        _delete(models.LabOrder, "lab_orders", models.LabOrder.id.in_(lab_order_ids))

    _delete(models.NurseAssessment, "nurse_assessments", models.NurseAssessment.patient_id == patient_id)

    invoice_ids = [row[0] for row in db.query(models.Invoice.id).filter(models.Invoice.patient_id == patient_id).all()]
    if invoice_ids:
        _delete(models.PaymentRecord, "payment_records", models.PaymentRecord.invoice_id.in_(invoice_ids))
        _delete(models.InvoiceItem, "invoice_items", models.InvoiceItem.invoice_id.in_(invoice_ids))
        _delete(models.ClinicRefund, "refunds", models.ClinicRefund.invoice_id.in_(invoice_ids))
        _delete(models.Invoice, "invoices", models.Invoice.id.in_(invoice_ids))

    _delete(models.ClinicCharge, "charges", models.ClinicCharge.patient_id == patient_id)
    _delete(models.Admission, "admissions", models.Admission.patient_id == patient_id)
    _delete(models.ClinicalVisit, "visits", models.ClinicalVisit.patient_id == patient_id)

    if hasattr(models, "PharmacyOrder"):
        _delete(models.PharmacyOrder, "pharmacy_orders", models.PharmacyOrder.patient_id == patient_id)

    _delete(models.Patient, "patients", models.Patient.id == patient_id)
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description="AASMA production data cleanup")
    parser.add_argument("--clinic-id", type=int, default=AASMA_CLINIC_ID)
    parser.add_argument("--execute", action="store_true", help="Apply deletions (default: dry-run)")
    parser.add_argument(
        "--all-patients",
        action="store_true",
        help="Delete ALL patients at the clinic (not only test name patterns)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        q = db.query(models.Patient).filter(
            models.Patient.clinic_id == args.clinic_id,
            models.Patient.is_archived.is_(False),
        )
        if not args.all_patients:
            pattern_filters = [models.Patient.last_name.op("~*")(pat) for pat in TEST_NAME_PATTERNS]
            q = q.filter(or_(*pattern_filters))

        patients = q.all()
        print(f"Clinic {args.clinic_id}: {len(patients)} patient(s) matched for cleanup")
        if not patients:
            print("Nothing to delete.")
            return 0

        total: dict[str, int] = {}
        for patient in patients:
            label = f"{patient.last_name} {patient.first_name} (#{patient.patient_number or patient.id})"
            print(f"  - {label}")
            if args.execute:
                row_counts = purge_patient(db, patient.id)
                for k, v in row_counts.items():
                    total[k] = total.get(k, 0) + v

        if args.execute:
            db.commit()
            print("Deleted:", total)
        else:
            print("Dry-run only. Re-run with --execute to apply.")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
