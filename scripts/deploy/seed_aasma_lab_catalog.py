#!/usr/bin/env python3
"""Create clinic_lab_tests table and seed AASMA catalog on production."""
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

from sqlalchemy import create_engine, inspect

from data.aasma_lab_catalog import AASMA_CLINIC_ID, AASMA_EXAM_COUNT, AASMA_CATEGORY_COUNT
from database import SessionLocal
from database_migrations import ensure_clinic_lab_tests_table
from services.lab_clinical_service import LabClinicalService


def main() -> int:
    engine = create_engine(PROD_URL)
    ensure_clinic_lab_tests_table(engine)
    insp = inspect(engine)
    print("clinic_lab_tests:", "OK" if "clinic_lab_tests" in insp.get_table_names() else "MISSING")

    db = SessionLocal()
    try:
        LabClinicalService.sync_aasma_catalog(db, clinic_id=AASMA_CLINIC_ID)
        payload = LabClinicalService.catalog_payload(db, clinic_id=AASMA_CLINIC_ID)
    finally:
        db.close()

    print("categories:", payload.get("total_categories"), "expected:", AASMA_CATEGORY_COUNT)
    print("exams:", payload.get("total_tests"), "expected:", AASMA_EXAM_COUNT)
    if payload.get("total_categories") != AASMA_CATEGORY_COUNT:
        return 1
    if payload.get("total_tests") != AASMA_EXAM_COUNT:
        return 1
    print("Seed OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
