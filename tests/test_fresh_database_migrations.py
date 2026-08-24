"""A pristine clinic database must be constructible through Alembic alone."""

from __future__ import annotations

import os
import subprocess
import sys

from sqlalchemy import create_engine, inspect, text


def test_alembic_upgrade_head_bootstraps_pristine_database(tmp_path):
    database_path = tmp_path / "fresh-clinic.db"
    database_url = f"sqlite:///{database_path}"
    env = {
        **os.environ,
        "DATABASE_URL": database_url,
        "SECRET_KEY": "fresh-migration-test-secret-key-32chars",
        "ENVIRONMENT": "development",
    }
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=os.path.dirname(os.path.dirname(__file__)),
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    engine = create_engine(database_url)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    assert {
        "users",
        "clinics",
        "patients",
        "patient_visit_workflows",
        "invoices",
        "api_client_idempotency_keys",
        "alembic_version",
    } <= tables
    with engine.connect() as connection:
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert revision == "20260824_0032_hospitalization_stay_fields"
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    assert {"first_name", "last_name"} <= user_columns

    patient_columns = {column["name"] for column in inspector.get_columns("patients")}
    assert {"clinic_id", "patient_number", "user_id"} <= patient_columns
    user_columns = {column["name"] for column in inspector.get_columns("users")}
    assert {"session_version", "token_version", "must_change_password"} <= user_columns
