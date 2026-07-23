#!/usr/bin/env python3
"""Remove AASMA clinic (id=17) test/demo clinical data — keep staff accounts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data.aasma_lab_catalog import AASMA_CLINIC_ID
from database import SessionLocal
from services.demo_patient_cleanup import cleanup_demo_patients


def main() -> int:
    parser = argparse.ArgumentParser(description="AASMA production data cleanup")
    parser.add_argument("--clinic-id", type=int, default=AASMA_CLINIC_ID)
    parser.add_argument("--execute", action="store_true", help="Apply deletions (default: dry-run)")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        result = cleanup_demo_patients(db, args.clinic_id, execute=args.execute)
        print(f"Clinic {args.clinic_id}: {result['matched']} patient(s) matched for cleanup")
        for p in result["patients"]:
            print(f"  - {p['last_name']} {p['first_name']} (#{p.get('patient_number') or p['id']})")
        if args.execute:
            print("Deleted:", result["deleted_counts"])
        else:
            print("Dry-run only. Re-run with --execute to apply.")
            print("Or call POST /platform/clinics/{id}/cleanup-demo-patients?execute=true")
        return 0
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
