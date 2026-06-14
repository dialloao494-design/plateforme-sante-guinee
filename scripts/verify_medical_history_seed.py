"""Verify 50 seeded patients retain longitudinal medical history."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import SessionLocal
import models
from models.user import User
from services.medical_history_service import MedicalHistoryService

SEED_MARKER = "sim_history_"


def main() -> int:
    db = SessionLocal()
    try:
        patients = (
            db.query(models.Patient)
            .filter(models.Patient.last_name.like(f"{SEED_MARKER}%"))
            .order_by(models.Patient.id)
            .all()
        )
        if len(patients) < 50:
            print(f"FAIL: expected 50 seeded patients, found {len(patients)}")
            return 1

        admin = db.query(User).filter(User.role == "admin").first()
        if not admin:
            print("FAIL: no admin user for read access")
            return 1

        ok = 0
        for p in patients:
            history = MedicalHistoryService.get_full_history(db, p.id, admin)
            consult_count = len(history.consultations)
            if consult_count < 2:
                print(f"FAIL: patient {p.id} has only {consult_count} consultations")
                return 1
            if not history.medical_record:
                print(f"FAIL: patient {p.id} missing permanent medical record")
                return 1
            if len(history.timeline) < 2:
                print(f"FAIL: patient {p.id} timeline too short")
                return 1
            ok += 1

        print(f"OK: {ok} patients with multi-visit longitudinal history verified")
        sample = patients[0]
        sample_history = MedicalHistoryService.get_full_history(db, sample.id, admin)
        print(
            f"Sample patient {sample.first_name} {sample.last_name}: "
            f"{len(sample_history.consultations)} consultations, "
            f"{len(sample_history.prescriptions)} prescriptions, "
            f"{len(sample_history.lab_results)} lab results, "
            f"{len(sample_history.timeline)} timeline days"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
