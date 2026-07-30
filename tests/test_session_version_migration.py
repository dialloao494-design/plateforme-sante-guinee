"""Migration recovery tests — users.session_version must appear for existing users."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text


ROOT = Path(__file__).resolve().parents[1]


def test_single_alembic_head():
    script = ScriptDirectory.from_config(Config(str(ROOT / "alembic.ini")))
    heads = script.get_heads()
    assert heads == ["20260730_0025_ensure_session_version"], heads


def test_upgrade_0025_recovers_missing_session_version_on_stamped_db(tmp_path):
    """Railway case: alembic at/after 0024 but users.session_version never applied."""
    db_path = tmp_path / "stamped_missing_col.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    email VARCHAR NOT NULL UNIQUE,
                    hashed_password VARCHAR NOT NULL,
                    role VARCHAR NOT NULL,
                    clinic_id INTEGER,
                    is_active BOOLEAN NOT NULL DEFAULT 1,
                    must_change_password BOOLEAN NOT NULL DEFAULT 0
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, role, is_active, must_change_password) "
                "VALUES (1, 'owner@clinic.test', 'hash', 'platform_owner', 1, 0)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, role, is_active, must_change_password) "
                "VALUES (2, 'doc@clinic.test', 'hash', 'doctor', 1, 0)"
            )
        )
        # Stamped as if 0024 completed, but DDL for session_version never landed.
        conn.execute(text("CREATE TABLE alembic_version (version_num VARCHAR(64) NOT NULL)"))
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) "
                "VALUES ('20260730_0024_security_wave0_identity')"
            )
        )
    engine.dispose()

    # Subprocess so alembic/env.py picks this DATABASE_URL (not the pytest shared engine).
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
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    assert "session_version" in cols
    assert "token_version" in cols

    with engine.connect() as conn:
        version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
        rows = conn.execute(
            text("SELECT id, email, session_version, token_version, role FROM users ORDER BY id")
        ).fetchall()
    assert version == "20260730_0025_ensure_session_version"
    assert len(rows) == 2
    assert rows[0].email == "owner@clinic.test"
    assert rows[0].session_version == 0
    assert rows[0].token_version == 0
    assert rows[1].email == "doc@clinic.test"
    assert {r.role for r in rows} == {"platform_owner", "doctor"}


def test_ensure_helper_adds_session_version_without_alembic(tmp_path):
    from database_migrations import ensure_user_session_security_columns

    db_path = tmp_path / "ensure_only.db"
    url = f"sqlite:///{db_path}"
    engine = create_engine(url)
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY,
                    email VARCHAR NOT NULL,
                    hashed_password VARCHAR NOT NULL,
                    role VARCHAR NOT NULL
                )
                """
            )
        )
        conn.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, role) "
                "VALUES (7, 'nurse@clinic.test', 'hash', 'nurse')"
            )
        )

    ensure_user_session_security_columns(engine)
    cols = {c["name"] for c in inspect(engine).get_columns("users")}
    assert "session_version" in cols
    assert "token_version" in cols
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id, session_version, token_version FROM users WHERE id = 7")
        ).one()
    assert row.session_version == 0
    assert row.token_version == 0


def test_login_works_after_session_version_migration(client, db_session, admin_user):
    """Auth path must read session_version successfully after schema is current."""
    assert getattr(admin_user, "session_version", None) is not None
    r = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass12!"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("access_token")
    me = client.get("/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200
