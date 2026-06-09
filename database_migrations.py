"""
Lightweight additive migrations for SQLite / Postgres without Alembic runs.
Called after SQLAlchemy create_all on startup.
"""

from __future__ import annotations

import logging
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)


def ensure_doctor_geolocation_columns(engine: Engine) -> None:
    insp = inspect(engine)
    if "doctors" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("doctors")}
    dialect = engine.dialect.name
    coltype = "DOUBLE PRECISION" if dialect == "postgresql" else "FLOAT"
    stmts: list[str] = []
    if "latitude" not in cols:
        stmts.append(f"ALTER TABLE doctors ADD COLUMN latitude {coltype}")
    if "longitude" not in cols:
        stmts.append(f"ALTER TABLE doctors ADD COLUMN longitude {coltype}")
    for stmt in stmts:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Applied doctor schema migration: %s", stmt)
        except Exception as exc:
            logger.warning("Doctor geo migration skipped or failed (%s): %s", stmt, exc)


def ensure_message_attachment_columns(engine: Engine) -> None:
    """Add opaque storage metadata columns for secure clinical attachments."""
    insp = inspect(engine)
    if "messages" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("messages")}
    dialect = engine.dialect.name
    varchar = "VARCHAR" if dialect == "sqlite" else "VARCHAR(255)"
    inttype = "INTEGER"
    stmts: list[str] = []
    if "attachment_storage_key" not in cols:
        stmts.append(f"ALTER TABLE messages ADD COLUMN attachment_storage_key {varchar}")
    if "attachment_mime_type" not in cols:
        stmts.append(f"ALTER TABLE messages ADD COLUMN attachment_mime_type {varchar}")
    if "attachment_size_bytes" not in cols:
        stmts.append(f"ALTER TABLE messages ADD COLUMN attachment_size_bytes {inttype}")
    for stmt in stmts:
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Applied message attachment schema migration: %s", stmt)
        except Exception as exc:
            logger.warning("Message attachment migration skipped or failed (%s): %s", stmt, exc)


def ensure_patient_dossier_schema(engine: Engine) -> None:
    """Add patient dossier columns and clinical record tables on existing deployments."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    date_type = "DATE"
    text_type = "TEXT"
    varchar32 = "VARCHAR(32)" if dialect == "postgresql" else "VARCHAR"
    varchar64 = "VARCHAR(64)" if dialect == "postgresql" else "VARCHAR"
    varchar255 = "VARCHAR(255)" if dialect == "postgresql" else "VARCHAR"

    if "patients" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("patients")}
        patient_stmts: list[str] = []
        if "date_of_birth" not in cols:
            patient_stmts.append(f"ALTER TABLE patients ADD COLUMN date_of_birth {date_type}")
        if "phone" not in cols:
            patient_stmts.append(f"ALTER TABLE patients ADD COLUMN phone {varchar32}")
        if "address" not in cols:
            patient_stmts.append(f"ALTER TABLE patients ADD COLUMN address {text_type}")
        if "emergency_contact" not in cols:
            patient_stmts.append(f"ALTER TABLE patients ADD COLUMN emergency_contact {varchar255}")
        if "created_at" not in cols:
            patient_stmts.append(
                f"ALTER TABLE patients ADD COLUMN created_at {datetime_type} DEFAULT CURRENT_TIMESTAMP"
            )
        if "updated_at" not in cols:
            patient_stmts.append(
                f"ALTER TABLE patients ADD COLUMN updated_at {datetime_type} DEFAULT CURRENT_TIMESTAMP"
            )
        for stmt in patient_stmts:
            try:
                with engine.begin() as conn:
                    conn.execute(text(stmt))
                logger.info("Applied patient dossier column migration: %s", stmt)
            except Exception as exc:
                logger.warning("Patient dossier column migration skipped or failed (%s): %s", stmt, exc)

    tables = set(insp.get_table_names())
    autoinc = " AUTOINCREMENT" if dialect == "sqlite" else ""

    if "clinical_notes" not in tables:
        stmt = f"""
            CREATE TABLE clinical_notes (
                id INTEGER PRIMARY KEY{autoinc},
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                doctor_id INTEGER REFERENCES doctors(id),
                appointment_id INTEGER REFERENCES rendezvous(id),
                note_type {varchar32} NOT NULL DEFAULT 'consultation',
                contenu {text_type} NOT NULL,
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created clinical_notes table")
        except Exception as exc:
            logger.warning("clinical_notes table migration skipped or failed: %s", exc)

    if "consultation_summaries" not in tables:
        stmt = f"""
            CREATE TABLE consultation_summaries (
                id INTEGER PRIMARY KEY{autoinc},
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                doctor_id INTEGER REFERENCES doctors(id),
                appointment_id INTEGER REFERENCES rendezvous(id),
                diagnostic {text_type},
                traitement {text_type},
                recommandations {text_type},
                created_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created consultation_summaries table")
        except Exception as exc:
            logger.warning("consultation_summaries table migration skipped or failed: %s", exc)

    if "patient_documents" not in tables:
        stmt = f"""
            CREATE TABLE patient_documents (
                id INTEGER PRIMARY KEY{autoinc},
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                uploaded_by INTEGER NOT NULL REFERENCES users(id),
                type_document {varchar64} NOT NULL,
                file_path {varchar255} NOT NULL,
                created_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created patient_documents table")
        except Exception as exc:
            logger.warning("patient_documents table migration skipped or failed: %s", exc)

    if "clinical_audit_logs" not in tables:
        stmt = f"""
            CREATE TABLE clinical_audit_logs (
                id INTEGER PRIMARY KEY{autoinc},
                actor_id INTEGER NOT NULL REFERENCES users(id),
                actor_role {varchar32} NOT NULL,
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                action {varchar32} NOT NULL,
                resource_type {varchar64} NOT NULL,
                resource_id INTEGER,
                timestamp {datetime_type} NOT NULL,
                ip {varchar64}
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created clinical_audit_logs table")
        except Exception as exc:
            logger.warning("clinical_audit_logs table migration skipped or failed: %s", exc)


def ensure_attachment_access_log_table(engine: Engine) -> None:
    """Create attachment download audit table on existing deployments (idempotent)."""
    insp = inspect(engine)
    if "attachment_access_logs" in insp.get_table_names():
        return
    dialect = engine.dialect.name
    varchar32 = "VARCHAR(32)" if dialect == "postgresql" else "VARCHAR"
    varchar64 = "VARCHAR(64)" if dialect == "postgresql" else "VARCHAR"
    varchar16 = "VARCHAR(16)" if dialect == "postgresql" else "VARCHAR"
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    stmt = f"""
        CREATE TABLE attachment_access_logs (
            id INTEGER PRIMARY KEY{' AUTOINCREMENT' if dialect == 'sqlite' else ''},
            message_id INTEGER NOT NULL REFERENCES messages(id),
            appointment_id INTEGER NOT NULL REFERENCES rendezvous(id),
            user_id INTEGER NOT NULL REFERENCES users(id),
            user_role {varchar32} NOT NULL,
            client_ip {varchar64},
            storage_kind {varchar16} NOT NULL DEFAULT 'secure',
            created_at {datetime_type} NOT NULL
        )
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(stmt))
        logger.info("Created attachment_access_logs audit table")
    except Exception as exc:
        logger.warning("Attachment access log table migration skipped or failed: %s", exc)
