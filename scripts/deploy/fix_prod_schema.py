#!/usr/bin/env python3
"""Apply critical production schema fixes and repair Alembic migration blockers."""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

PROD_URL = (
    "postgresql://postgres:nWXqmNzOziOMttMreQYSnTQXkyAmivtE@shortline.proxy.rlwy.net:46725/railway"
)
os.environ["DATABASE_URL"] = PROD_URL

from sqlalchemy import create_engine, inspect, text

from database_migrations import (
    ensure_clinic_lab_tests_table,
    ensure_doctor_medicine_deliveries_table,
    ensure_patient_intake_fields,
    ensure_reception_his_schema,
)

ALLOWED = (
    "patient",
    "doctor",
    "platform_owner",
    "platform_admin",
    "clinic_admin",
    "admin",
    "receptionist",
    "cashier",
    "lab_technician",
    "pharmacist",
    "nutritionist",
    "midwife",
)


def main() -> int:
    engine = create_engine(PROD_URL)

    with engine.connect() as conn:
        roles = [r[0] for r in conn.execute(text("SELECT DISTINCT role FROM users ORDER BY role"))]
        print("Current roles:", roles)
        bad = conn.execute(
            text(
                "SELECT id, email, role FROM users "
                "WHERE role NOT IN :allowed"
            ),
            {"allowed": ALLOWED},
        ).fetchall()
        print("Invalid role rows:", len(bad))
        for row in bad:
            print(" ", row)

    ensure_patient_intake_fields(engine)
    ensure_reception_his_schema(engine)
    ensure_doctor_medicine_deliveries_table(engine)
    ensure_clinic_lab_tests_table(engine)

    from data.aasma_lab_catalog import AASMA_CLINIC_ID
    from database import SessionLocal
    from services.lab_clinical_service import LabClinicalService

    db = SessionLocal()
    try:
        LabClinicalService.sync_aasma_catalog(db, clinic_id=AASMA_CLINIC_ID)
        payload = LabClinicalService.catalog_payload(db, clinic_id=AASMA_CLINIC_ID)
        print(
            "AASMA lab catalog:",
            payload.get("total_categories"),
            "categories,",
            payload.get("total_tests"),
            "exams",
        )
    finally:
        db.close()

    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("patients")}
    for col in ("mother_name", "profession", "quartier", "visit_destination"):
        print(f"patients.{col}:", "OK" if col in cols else "MISSING")
    print(
        "doctor_medicine_deliveries:",
        "OK" if "doctor_medicine_deliveries" in insp.get_table_names() else "MISSING",
    )

    # Map legacy roles before Alembic constraint migration
    role_map = {
        "nurse": "midwife",
        "lab": "lab_technician",
        "pharmacy": "pharmacist",
        "reception": "receptionist",
    }
    with engine.begin() as conn:
        for old, new in role_map.items():
            res = conn.execute(
                text("UPDATE users SET role = :new WHERE role = :old"),
                {"old": old, "new": new},
            )
            if res.rowcount:
                print(f"Remapped role {old!r} -> {new!r}: {res.rowcount} rows")

        remaining = conn.execute(
            text("SELECT id, email, role FROM users WHERE role NOT IN :allowed"),
            {"allowed": ALLOWED},
        ).fetchall()
        if remaining:
            print("Still invalid after remap:")
            for row in remaining:
                print(" ", row)
                conn.execute(
                    text("UPDATE users SET role = 'patient' WHERE id = :id"),
                    {"id": row[0]},
                )
                print(f"  -> forced to patient for id={row[0]}")

    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        print("Alembic before upgrade:", row[0] if row else None)

    command.upgrade(cfg, "head")
    print("Alembic upgrade head completed")

    with engine.connect() as conn:
        row = conn.execute(text("SELECT version_num FROM alembic_version")).fetchone()
        print("Alembic after upgrade:", row[0] if row else None)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
