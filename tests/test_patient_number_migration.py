"""patient_number backfill logic and Alembic 0028 migration."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from core.patient_number import backfill_patient_numbers, format_patient_number

ROOT = Path(__file__).resolve().parents[1]


class TestFormatPatientNumber:
    def test_canonical_format(self):
        assert format_patient_number(17, 42) == "PAT-017-000042"

    def test_null_clinic_uses_zero_pad(self):
        assert format_patient_number(None, 9) == "PAT-000-000009"


class TestBackfillPatientNumbers:
    def test_backfills_null_rows(self):
        rows = [
            {"id": 3, "clinic_id": 1, "patient_number": None},
            {"id": 4, "clinic_id": 1, "patient_number": "PAT-001-000004"},
        ]
        updates = backfill_patient_numbers(rows)
        assert updates == {3: "PAT-001-000003"}

    def test_resolves_duplicate_numbers_per_clinic(self):
        rows = [
            {"id": 2, "clinic_id": 5, "patient_number": "PAT-005-000099"},
            {"id": 9, "clinic_id": 5, "patient_number": "PAT-005-000099"},
        ]
        updates = backfill_patient_numbers(rows)
        assert updates[2] == "PAT-005-000002"
        assert updates[9] == "PAT-005-000009"

    def test_does_not_touch_unique_numbers(self):
        rows = [{"id": 11, "clinic_id": 2, "patient_number": "LEGACY-11"}]
        assert backfill_patient_numbers(rows) == {}


def test_single_alembic_head_includes_patient_number_integrity():
    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    heads = script.get_heads()
    assert heads == ["20260824_0033_clinic_onboarding"], heads


def test_upgrade_0028_backfills_null_patient_number(tmp_path):
    db_path = tmp_path / "patient_number_backfill.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE patients (
                    id INTEGER PRIMARY KEY,
                    clinic_id INTEGER,
                    patient_number VARCHAR(32)
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO patients (id, clinic_id, patient_number) VALUES "
                "(7, 3, NULL), (8, 3, 'PAT-003-000008')"
            )
        )
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)"))
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('20260806_0027_api_client_idempotency')"
            )
        )
    engine.dispose()

    env = os.environ.copy()
    env["DATABASE_URL"] = url
    env["SECRET_KEY"] = "test-secret-key-for-pytest-only-32chars-min"
    env["ENVIRONMENT"] = "development"
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from alembic.config import Config; from alembic import command; "
            "command.upgrade(Config('alembic.ini'), 'head')",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    engine = create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT id, patient_number FROM patients ORDER BY id")
        ).fetchall()
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
    assert version == "20260824_0033_clinic_onboarding"
    assert rows[0].patient_number == "PAT-003-000007"
    assert rows[1].patient_number == "PAT-003-000008"
    indexes = {idx["name"] for idx in inspect(engine).get_indexes("patients")}
    assert "uq_patients_clinic_patient_number" in indexes


def test_upgrade_0028_resolves_duplicate_patient_numbers(tmp_path):
    db_path = tmp_path / "patient_number_dupes.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE patients (
                    id INTEGER PRIMARY KEY,
                    clinic_id INTEGER,
                    patient_number VARCHAR(32)
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO patients (id, clinic_id, patient_number) VALUES "
                "(2, 1, 'PAT-001-000099'), (5, 1, 'PAT-001-000099')"
            )
        )
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)"))
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('20260806_0027_api_client_idempotency')"
            )
        )
    engine.dispose()

    env = os.environ.copy()
    env["DATABASE_URL"] = url
    env["SECRET_KEY"] = "test-secret-key-for-pytest-only-32chars-min"
    env["ENVIRONMENT"] = "development"
    proc = subprocess.run(
        [
            sys.executable,
            "-c",
            "from alembic.config import Config; from alembic import command; "
            "command.upgrade(Config('alembic.ini'), 'head')",
        ],
        cwd=str(ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, proc.stdout + "\n" + proc.stderr

    engine = create_engine(url)
    with engine.connect() as conn:
        rows = {
            row.id: row.patient_number
            for row in conn.execute(
                text("SELECT id, patient_number FROM patients ORDER BY id")
            ).fetchall()
        }
    assert rows[2] == "PAT-001-000002"
    assert rows[5] == "PAT-001-000005"
