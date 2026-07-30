"""Production recovery: 0017+ must apply when schema already exists but stamp lags."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[1]


def test_single_alembic_head_still_0025():
    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    assert script.get_heads() == ["20260730_0025_ensure_session_version"]


def test_upgrade_from_0016_with_existing_0017_tables(tmp_path):
    """Railway case: alembic at 0016 while nutrition/immunization tables already exist."""
    db_path = tmp_path / "recover_0017.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(128) NOT NULL)"))
        conn.execute(text("CREATE TABLE clinics (id INTEGER PRIMARY KEY, name VARCHAR(255))"))
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    email VARCHAR(255) NOT NULL,
                    hashed_password VARCHAR(255) NOT NULL,
                    role VARCHAR(50) NOT NULL DEFAULT 'patient',
                    clinic_id INTEGER,
                    is_active BOOLEAN NOT NULL DEFAULT 1
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE patients (
                    id INTEGER PRIMARY KEY,
                    clinic_id INTEGER,
                    full_name VARCHAR(255)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE consultations (
                    id INTEGER PRIMARY KEY,
                    clinic_id INTEGER,
                    patient_id INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE clinical_visits (
                    id INTEGER PRIMARY KEY,
                    clinic_id INTEGER,
                    patient_id INTEGER
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE nutrition_assessments (
                    id INTEGER PRIMARY KEY,
                    clinic_id INTEGER NOT NULL,
                    patient_id INTEGER NOT NULL,
                    consultation_id INTEGER,
                    recorded_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE vaccine_schedule_items (
                    id INTEGER PRIMARY KEY,
                    vaccine_code VARCHAR(32) NOT NULL,
                    vaccine_name VARCHAR(128) NOT NULL,
                    dose_label VARCHAR(64) NOT NULL,
                    age_months INTEGER NOT NULL,
                    grace_days INTEGER NOT NULL DEFAULT 14,
                    is_active BOOLEAN NOT NULL DEFAULT 1
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE immunization_records (
                    id INTEGER PRIMARY KEY,
                    clinic_id INTEGER NOT NULL,
                    patient_id INTEGER NOT NULL,
                    vaccine_code VARCHAR(32) NOT NULL,
                    vaccine_name VARCHAR(128) NOT NULL,
                    administered_at DATE NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                """
                CREATE TABLE password_reset_tokens (
                    id INTEGER PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    token_hash VARCHAR(128) NOT NULL,
                    expires_at DATETIME NOT NULL,
                    created_at DATETIME NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('20260624_0016_platform_owner')"
            )
        )
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, role) "
                "VALUES (1, 'nurse@test.com', 'x', 'nurse')"
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
    tables = set(inspect(engine).get_table_names())
    assert "nutrition_assessments" in tables
    assert "patient_visit_workflows" in tables
    with engine.connect() as conn:
        rev = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        role = conn.execute(text("SELECT role FROM users WHERE id = 1")).scalar()
        user_count = conn.execute(text("SELECT COUNT(*) FROM users")).scalar()
    assert rev == "20260730_0025_ensure_session_version"
    assert role == "nurse"
    assert user_count == 1
    engine.dispose()
