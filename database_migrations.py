"""
Lightweight additive migrations for SQLite / Postgres without Alembic runs.

Called after SQLAlchemy create_all on startup in **local development only**.
Deployed, Railway, and clinic-node environments must use Alembic exclusively —
see main._alembic_only_schema() and run_alembic_upgrade_head(fail_closed=True).
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
                clinic_id INTEGER REFERENCES clinics(id),
                patient_id INTEGER REFERENCES patients(id),
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


def ensure_clinic_charges_table(engine: Engine) -> None:
    """Create in-clinic billing charges table (idempotent)."""
    insp = inspect(engine)
    if "clinic_charges" in insp.get_table_names():
        return
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    autoinc = " AUTOINCREMENT" if dialect == "sqlite" else ""
    stmt = f"""
        CREATE TABLE clinic_charges (
            id INTEGER PRIMARY KEY{autoinc},
            clinic_id INTEGER NOT NULL REFERENCES clinics(id),
            patient_id INTEGER NOT NULL REFERENCES patients(id),
            charge_type VARCHAR(32) NOT NULL,
            source_type VARCHAR(32) NOT NULL,
            source_id INTEGER NOT NULL,
            description TEXT NOT NULL,
            amount_gnf INTEGER NOT NULL DEFAULT 0,
            payment_status VARCHAR(32) NOT NULL DEFAULT 'pending',
            payment_method VARCHAR(32),
            recorded_by_user_id INTEGER REFERENCES users(id),
            paid_at {datetime_type},
            created_at {datetime_type} NOT NULL,
            updated_at {datetime_type} NOT NULL
        )
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(stmt))
        logger.info("Created clinic_charges table")
    except Exception as exc:
        logger.warning("clinic_charges table migration skipped or failed: %s", exc)


def ensure_clinical_audit_clinic_id(engine: Engine) -> None:
    """Add clinic_id to clinical_audit_logs on existing SQLite/Postgres deployments."""
    insp = inspect(engine)
    if "clinical_audit_logs" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("clinical_audit_logs")}
    if "clinic_id" in cols:
        return
    dialect = engine.dialect.name
    try:
        with engine.begin() as conn:
            if dialect == "sqlite":
                conn.execute(text("ALTER TABLE clinical_audit_logs ADD COLUMN clinic_id INTEGER"))
            else:
                conn.execute(text("ALTER TABLE clinical_audit_logs ADD COLUMN clinic_id INTEGER REFERENCES clinics(id)"))
        logger.info("Added clinic_id column to clinical_audit_logs")
    except Exception as exc:
        logger.warning("clinical_audit_logs clinic_id migration skipped or failed: %s", exc)


def ensure_clinical_audit_patient_nullable(engine: Engine) -> None:
    """Allow NULL patient_id for denied-access and system audit rows (SQLite rebuild)."""
    insp = inspect(engine)
    if "clinical_audit_logs" not in insp.get_table_names():
        return
    cols = {c["name"]: c for c in insp.get_columns("clinical_audit_logs")}
    if "patient_id" not in cols:
        return
    if cols["patient_id"].get("nullable"):
        return
    dialect = engine.dialect.name
    if dialect != "sqlite":
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE clinical_audit_logs ALTER COLUMN patient_id DROP NOT NULL"))
            logger.info("Relaxed patient_id NOT NULL on clinical_audit_logs")
        except Exception as exc:
            logger.warning("clinical_audit_logs patient_id nullable migration skipped: %s", exc)
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE clinical_audit_logs_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    actor_id INTEGER NOT NULL REFERENCES users(id),
                    actor_role VARCHAR NOT NULL,
                    clinic_id INTEGER REFERENCES clinics(id),
                    patient_id INTEGER REFERENCES patients(id),
                    action VARCHAR NOT NULL,
                    resource_type VARCHAR NOT NULL,
                    resource_id INTEGER,
                    timestamp DATETIME NOT NULL,
                    ip VARCHAR
                )
            """))
            conn.execute(text("""
                INSERT INTO clinical_audit_logs_new
                (id, actor_id, actor_role, clinic_id, patient_id, action, resource_type, resource_id, timestamp, ip)
                SELECT id, actor_id, actor_role, clinic_id, patient_id, action, resource_type, resource_id, timestamp, ip
                FROM clinical_audit_logs
            """))
            conn.execute(text("DROP TABLE clinical_audit_logs"))
            conn.execute(text("ALTER TABLE clinical_audit_logs_new RENAME TO clinical_audit_logs"))
        logger.info("Rebuilt clinical_audit_logs with nullable patient_id")
    except Exception as exc:
        logger.warning("clinical_audit_logs patient_id rebuild skipped: %s", exc)


def ensure_medical_history_schema(engine: Engine) -> None:
    """Medical history tables and soft-delete columns (idempotent)."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    date_type = "DATE"
    text_type = "TEXT"
    bool_type = "BOOLEAN" if dialect == "postgresql" else "INTEGER"
    float_type = "DOUBLE PRECISION" if dialect == "postgresql" else "FLOAT"
    autoinc = " AUTOINCREMENT" if dialect == "sqlite" else ""

    if "patients" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("patients")}
        for col, stmt in [
            ("is_archived", f"ALTER TABLE patients ADD COLUMN is_archived {bool_type} NOT NULL DEFAULT 0"),
            ("archived_at", f"ALTER TABLE patients ADD COLUMN archived_at {datetime_type}"),
        ]:
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(stmt))
                    logger.info("Applied patients migration: %s", col)
                except Exception as exc:
                    logger.warning("patients %s migration skipped: %s", col, exc)

    for table, col in [
        ("consultations", "deleted_at"),
        ("lab_orders", "deleted_at"),
        ("prescriptions", "deleted_at"),
    ]:
        if table in insp.get_table_names():
            cols = {c["name"] for c in insp.get_columns(table)}
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {datetime_type}"))
                    logger.info("Added %s to %s", col, table)
                except Exception as exc:
                    logger.warning("%s.%s migration skipped: %s", table, col, exc)

    tables = set(insp.get_table_names())

    if "patient_medical_records" not in tables:
        stmt = f"""
            CREATE TABLE patient_medical_records (
                id INTEGER PRIMARY KEY{autoinc},
                patient_id INTEGER NOT NULL UNIQUE REFERENCES patients(id),
                blood_type VARCHAR(8),
                general_notes {text_type},
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created patient_medical_records table")
        except Exception as exc:
            logger.warning("patient_medical_records migration failed: %s", exc)

    if "patient_allergies" not in tables:
        stmt = f"""
            CREATE TABLE patient_allergies (
                id INTEGER PRIMARY KEY{autoinc},
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                allergen VARCHAR(255) NOT NULL,
                severity VARCHAR(32) NOT NULL DEFAULT 'moderate',
                reaction {text_type},
                recorded_by_user_id INTEGER REFERENCES users(id),
                is_active {bool_type} NOT NULL DEFAULT 1,
                deleted_at {datetime_type},
                created_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created patient_allergies table")
        except Exception as exc:
            logger.warning("patient_allergies migration failed: %s", exc)

    if "patient_chronic_conditions" not in tables:
        stmt = f"""
            CREATE TABLE patient_chronic_conditions (
                id INTEGER PRIMARY KEY{autoinc},
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                condition_name VARCHAR(255) NOT NULL,
                diagnosed_at {date_type},
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                notes {text_type},
                recorded_by_user_id INTEGER REFERENCES users(id),
                deleted_at {datetime_type},
                created_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created patient_chronic_conditions table")
        except Exception as exc:
            logger.warning("patient_chronic_conditions migration failed: %s", exc)

    if "patient_vital_signs" not in tables:
        stmt = f"""
            CREATE TABLE patient_vital_signs (
                id INTEGER PRIMARY KEY{autoinc},
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                consultation_id INTEGER REFERENCES consultations(id),
                bp_systolic INTEGER,
                bp_diastolic INTEGER,
                heart_rate INTEGER,
                temperature_c {float_type},
                weight_kg {float_type},
                height_cm {float_type},
                spo2 INTEGER,
                notes {text_type},
                recorded_by_user_id INTEGER REFERENCES users(id),
                recorded_at {datetime_type} NOT NULL,
                deleted_at {datetime_type}
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created patient_vital_signs table")
        except Exception as exc:
            logger.warning("patient_vital_signs migration failed: %s", exc)

    if "follow_up_schedules" not in tables:
        stmt = f"""
            CREATE TABLE follow_up_schedules (
                id INTEGER PRIMARY KEY{autoinc},
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                consultation_id INTEGER REFERENCES consultations(id),
                doctor_id INTEGER NOT NULL REFERENCES doctors(id),
                scheduled_date {date_type} NOT NULL,
                interval_type VARCHAR(16) NOT NULL,
                visit_type VARCHAR(32) NOT NULL DEFAULT 'follow_up',
                reason {text_type},
                clinical_notes {text_type},
                status VARCHAR(32) NOT NULL DEFAULT 'scheduled',
                follow_up_appointment_id INTEGER REFERENCES rendezvous(id),
                created_by_user_id INTEGER REFERENCES users(id),
                deleted_at {datetime_type},
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created follow_up_schedules table")
        except Exception as exc:
            logger.warning("follow_up_schedules migration failed: %s", exc)


def ensure_hospitalization_schema(engine: Engine) -> None:
    """Create admission / bed management tables on existing deployments."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    text_type = "TEXT"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"

    if "hospital_rooms" not in tables:
        stmt = f"""
            CREATE TABLE hospital_rooms (
                id INTEGER PRIMARY KEY{autoinc},
                clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                ward_name VARCHAR(128) NOT NULL,
                room_number VARCHAR(32) NOT NULL,
                room_type VARCHAR(64) NOT NULL DEFAULT 'general',
                capacity INTEGER NOT NULL DEFAULT 1,
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                notes {text_type},
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created hospital_rooms table")
        except Exception as exc:
            logger.warning("hospital_rooms migration failed: %s", exc)

    if "hospital_beds" not in tables:
        stmt = f"""
            CREATE TABLE hospital_beds (
                id INTEGER PRIMARY KEY{autoinc},
                room_id INTEGER NOT NULL REFERENCES hospital_rooms(id),
                bed_number VARCHAR(32) NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'available',
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created hospital_beds table")
        except Exception as exc:
            logger.warning("hospital_beds migration failed: %s", exc)

    if "admissions" not in tables:
        stmt = f"""
            CREATE TABLE admissions (
                id INTEGER PRIMARY KEY{autoinc},
                clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                consultation_id INTEGER REFERENCES consultations(id),
                admission_number VARCHAR(32) NOT NULL UNIQUE,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                reason {text_type},
                diagnosis_summary {text_type},
                notes {text_type},
                admitted_by_user_id INTEGER REFERENCES users(id),
                admitted_at {datetime_type},
                discharged_at {datetime_type},
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created admissions table")
        except Exception as exc:
            logger.warning("admissions migration failed: %s", exc)

    if "patient_stays" not in tables:
        stmt = f"""
            CREATE TABLE patient_stays (
                id INTEGER PRIMARY KEY{autoinc},
                admission_id INTEGER NOT NULL REFERENCES admissions(id),
                bed_id INTEGER NOT NULL REFERENCES hospital_beds(id),
                assigned_at {datetime_type} NOT NULL,
                released_at {datetime_type},
                is_current BOOLEAN NOT NULL DEFAULT 1,
                transfer_reason {text_type},
                assigned_by_user_id INTEGER REFERENCES users(id),
                created_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created patient_stays table")
        except Exception as exc:
            logger.warning("patient_stays migration failed: %s", exc)


def ensure_discharge_schema(engine: Engine) -> None:
    """Create discharge_summaries table on existing deployments."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    if "discharge_summaries" in tables:
        return
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    text_type = "TEXT"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"
    stmt = f"""
        CREATE TABLE discharge_summaries (
            id INTEGER PRIMARY KEY{autoinc},
            clinic_id INTEGER NOT NULL REFERENCES clinics(id),
            patient_id INTEGER NOT NULL REFERENCES patients(id),
            visit_id INTEGER REFERENCES clinical_visits(id),
            admission_id INTEGER REFERENCES admissions(id),
            consultation_id INTEGER REFERENCES consultations(id),
            invoice_id INTEGER REFERENCES invoices(id),
            discharge_type VARCHAR(32) NOT NULL DEFAULT 'ambulatory',
            status VARCHAR(32) NOT NULL DEFAULT 'draft',
            diagnoses {text_type},
            procedures {text_type},
            medications {text_type},
            clinical_summary {text_type},
            follow_up_instructions {text_type},
            invoice_validated BOOLEAN NOT NULL DEFAULT 0,
            archived_to_emr BOOLEAN NOT NULL DEFAULT 0,
            discharged_by_user_id INTEGER REFERENCES users(id),
            discharged_at {datetime_type},
            created_at {datetime_type} NOT NULL,
            updated_at {datetime_type} NOT NULL
        )
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(stmt))
        logger.info("Created discharge_summaries table")
    except Exception as exc:
        logger.warning("discharge_summaries migration failed: %s", exc)


def ensure_radiology_schema(engine: Engine) -> None:
    """Create imaging_orders and imaging_results tables."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    text_type = "TEXT"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"
    if "imaging_orders" not in tables:
        stmt = f"""
            CREATE TABLE imaging_orders (
                id INTEGER PRIMARY KEY{autoinc},
                clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                consultation_id INTEGER NOT NULL REFERENCES consultations(id),
                modality VARCHAR(32) NOT NULL,
                body_part VARCHAR(128),
                clinical_indication {text_type},
                priority VARCHAR(16) NOT NULL DEFAULT 'routine',
                status VARCHAR(32) NOT NULL DEFAULT 'ordered',
                scheduled_at {datetime_type},
                ordered_by_user_id INTEGER REFERENCES users(id),
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created imaging_orders table")
        except Exception as exc:
            logger.warning("imaging_orders migration failed: %s", exc)
    if "imaging_results" not in tables:
        stmt = f"""
            CREATE TABLE imaging_results (
                id INTEGER PRIMARY KEY{autoinc},
                order_id INTEGER NOT NULL REFERENCES imaging_orders(id),
                findings {text_type},
                impression {text_type},
                recommendations {text_type},
                attachment_url {text_type},
                reported_by_user_id INTEGER REFERENCES users(id),
                validated_by_user_id INTEGER REFERENCES users(id),
                reported_at {datetime_type},
                validated_at {datetime_type},
                status VARCHAR(32) NOT NULL DEFAULT 'draft',
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created imaging_results table")
        except Exception as exc:
            logger.warning("imaging_results migration failed: %s", exc)


def ensure_reminders_schema(engine: Engine) -> None:
    """Create appointment_reminders and reminder_events tables."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    text_type = "TEXT"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"
    if "appointment_reminders" not in tables:
        stmt = f"""
            CREATE TABLE appointment_reminders (
                id INTEGER PRIMARY KEY{autoinc},
                appointment_id INTEGER NOT NULL REFERENCES rendezvous(id),
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                channel VARCHAR(32) NOT NULL DEFAULT 'whatsapp',
                reminder_type VARCHAR(16) NOT NULL,
                scheduled_at {datetime_type} NOT NULL,
                sent_at {datetime_type},
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                whatsapp_message_id VARCHAR(128),
                created_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created appointment_reminders table")
        except Exception as exc:
            logger.warning("appointment_reminders migration failed: %s", exc)
    if "reminder_events" not in tables:
        stmt = f"""
            CREATE TABLE reminder_events (
                id INTEGER PRIMARY KEY{autoinc},
                reminder_id INTEGER NOT NULL REFERENCES appointment_reminders(id),
                event_type VARCHAR(32) NOT NULL,
                payload {text_type},
                created_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created reminder_events table")
        except Exception as exc:
            logger.warning("reminder_events migration failed: %s", exc)


def ensure_user_roles_check_constraint(engine: Engine) -> None:
    """Ensure users.role allows nutritionist and midwife (idempotent on Postgres)."""
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    dialect = engine.dialect.name
    roles = (
        "'patient', 'doctor', 'platform_owner', 'platform_admin', 'clinic_admin', 'admin', "
        "'receptionist', 'cashier', 'lab_technician', 'pharmacist', 'nutritionist', 'midwife', "
        "'pev_agent', 'nurse'"
    )
    check_sql = f"role IN ({roles})"
    try:
        with engine.begin() as conn:
            if dialect == "postgresql":
                conn.execute(text("ALTER TABLE users DROP CONSTRAINT IF EXISTS ck_users_role_allowed"))
                conn.execute(
                    text(f"ALTER TABLE users ADD CONSTRAINT ck_users_role_allowed CHECK ({check_sql})")
                )
        logger.info("Ensured users role check constraint includes clinical module roles")
    except Exception as exc:
        logger.warning("users role constraint migration skipped: %s", exc)


def normalize_legacy_user_roles(engine: Engine) -> None:
    """Lowercase roles and map legacy aliases (medecin → doctor) in existing rows."""
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE users SET role = LOWER(TRIM(role)) WHERE role IS NOT NULL"))
            for legacy, canonical in (
                ("medecin", "doctor"),
                ("médecin", "doctor"),
                ("physician", "doctor"),
                ("professional", "doctor"),
                ("praticien", "doctor"),
            ):
                conn.execute(
                    text("UPDATE users SET role = :canonical WHERE role = :legacy"),
                    {"legacy": legacy, "canonical": canonical},
                )
        logger.info("Normalized legacy user roles in users.role")
    except Exception as exc:
        logger.warning("normalize_legacy_user_roles skipped: %s", exc)


def ensure_alembic_version_column(engine: Engine) -> None:
    """Widen alembic_version.version_num — Railway Postgres defaults to VARCHAR(32)."""
    insp = inspect(engine)
    if "alembic_version" not in insp.get_table_names():
        return
    dialect = engine.dialect.name
    try:
        with engine.begin() as conn:
            if dialect == "postgresql":
                conn.execute(
                    text(
                        "ALTER TABLE alembic_version "
                        "ALTER COLUMN version_num TYPE VARCHAR(64) "
                        "USING version_num::varchar(64)"
                    )
                )
            elif dialect == "sqlite":
                # SQLite cannot ALTER COLUMN type easily; recreate if too narrow.
                row = conn.execute(text("PRAGMA table_info(alembic_version)")).fetchall()
                version_col = next((r for r in row if r[1] == "version_num"), None)
                if version_col and "32" in str(version_col[2]):
                    conn.execute(text("ALTER TABLE alembic_version RENAME TO alembic_version_old"))
                    conn.execute(
                        text(
                            "CREATE TABLE alembic_version "
                            "(version_num VARCHAR(64) NOT NULL PRIMARY KEY)"
                        )
                    )
                    conn.execute(
                        text(
                            "INSERT INTO alembic_version (version_num) "
                            "SELECT version_num FROM alembic_version_old"
                        )
                    )
                    conn.execute(text("DROP TABLE alembic_version_old"))
        logger.info("Ensured alembic_version.version_num width >= 64")
    except Exception as exc:
        logger.warning("alembic_version column widen skipped: %s", exc)


def ensure_user_session_security_columns(engine: Engine) -> None:
    """
    Ensure users.session_version + Wave0 identity columns exist.

    Production crash evidence: UndefinedColumn users.session_version.
    create_all() does not add columns to existing tables — this helper must run
    after Alembic (and as a failsafe if Alembic was stamped without DDL).
    """
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    dialect = engine.dialect.name
    cols = {c["name"] for c in insp.get_columns("users")}

    def _add_int_not_null(column: str) -> None:
        nonlocal cols
        if column in cols:
            return
        if dialect == "postgresql":
            stmt = (
                f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} "
                "INTEGER NOT NULL DEFAULT 0"
            )
        else:
            stmt = f"ALTER TABLE users ADD COLUMN {column} INTEGER NOT NULL DEFAULT 0"
        with engine.begin() as conn:
            conn.execute(text(stmt))
            conn.execute(text(f"UPDATE users SET {column} = 0 WHERE {column} IS NULL"))
        logger.info("Added users.%s", column)
        cols.add(column)

    def _add_bool_not_null(column: str, default: str = "false") -> None:
        nonlocal cols
        if column in cols:
            return
        if dialect == "postgresql":
            stmt = (
                f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} "
                f"BOOLEAN NOT NULL DEFAULT {default}"
            )
        else:
            stmt = (
                f"ALTER TABLE users ADD COLUMN {column} BOOLEAN NOT NULL DEFAULT 0"
            )
        with engine.begin() as conn:
            conn.execute(text(stmt))
        logger.info("Added users.%s", column)
        cols.add(column)

    def _add_nullable(column: str, sql_type: str) -> None:
        nonlocal cols
        if column in cols:
            return
        if dialect == "postgresql":
            stmt = f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {column} {sql_type}"
        else:
            stmt = f"ALTER TABLE users ADD COLUMN {column} {sql_type}"
        with engine.begin() as conn:
            conn.execute(text(stmt))
        logger.info("Added users.%s", column)
        cols.add(column)

    _add_int_not_null("session_version")
    _add_int_not_null("token_version")
    _add_int_not_null("failed_login_attempts")
    _add_bool_not_null("mfa_enabled", "false")
    _add_nullable("locked_until", "TIMESTAMP" if dialect == "postgresql" else "DATETIME")
    _add_nullable("password_changed_at", "TIMESTAMP" if dialect == "postgresql" else "DATETIME")
    _add_nullable("last_login_at", "TIMESTAMP" if dialect == "postgresql" else "DATETIME")
    _add_nullable("mfa_secret", "VARCHAR")

    # Final verification — raise so entrypoint/startup can fail closed.
    insp = inspect(engine)
    cols = {c["name"] for c in insp.get_columns("users")}
    missing = sorted({"session_version", "token_version"} - cols)
    if missing:
        raise RuntimeError(
            "users security columns still missing after ensure_user_session_security_columns: "
            + ", ".join(missing)
        )


def ensure_single_platform_owner_index(engine: Engine) -> None:
    """Enforce at most one platform_owner account (partial unique index)."""
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    dialect = engine.dialect.name
    indexes = {idx["name"] for idx in insp.get_indexes("users")}
    if "uq_users_single_platform_owner" in indexes:
        return
    try:
        with engine.begin() as conn:
            # Demote extras before unique index — duplicate platform_owner rows
            # from historical /platform/setup races otherwise crash production boot.
            conn.execute(
                text(
                    """
                    UPDATE users
                    SET role = 'patient',
                        is_active = false
                    WHERE role = 'platform_owner'
                      AND id NOT IN (
                        SELECT id FROM (
                          SELECT MIN(id) AS id FROM users WHERE role = 'platform_owner'
                        ) keeper
                      )
                    """
                )
            )
            conn.execute(
                text(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_users_single_platform_owner "
                    "ON users (role) WHERE role = 'platform_owner'"
                )
            )
        logger.info("Applied unique partial index uq_users_single_platform_owner")
    except Exception as exc:
        logger.warning("uq_users_single_platform_owner migration skipped: %s", exc)


def ensure_patient_user_id_unique(engine: Engine) -> None:
    """Multi-tenant patients: clinic_id + composite (clinic_id, user_id) uniqueness."""
    insp = inspect(engine)
    if "patients" not in insp.get_table_names():
        return
    dialect = engine.dialect.name
    cols = {c["name"] for c in insp.get_columns("patients")}

    if "clinic_id" not in cols:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE patients ADD COLUMN clinic_id INTEGER"))
            logger.info("Added patients.clinic_id column")
        except Exception as exc:
            logger.warning("patients.clinic_id migration skipped: %s", exc)

    indexes = {idx["name"] for idx in insp.get_indexes("patients")}
    if "uq_patients_user_id" in indexes:
        try:
            with engine.begin() as conn:
                conn.execute(text("DROP INDEX uq_patients_user_id"))
            logger.info("Dropped legacy uq_patients_user_id index")
        except Exception as exc:
            logger.warning("Could not drop uq_patients_user_id: %s", exc)

    if "uq_patients_clinic_user" not in indexes:
        try:
            with engine.begin() as conn:
                if dialect == "sqlite":
                    conn.execute(
                        text(
                            "CREATE UNIQUE INDEX IF NOT EXISTS uq_patients_clinic_user "
                            "ON patients (clinic_id, user_id)"
                        )
                    )
                else:
                    conn.execute(
                        text(
                            "CREATE UNIQUE INDEX uq_patients_clinic_user "
                            "ON patients (clinic_id, user_id) "
                            "WHERE user_id IS NOT NULL"
                        )
                    )
            logger.info("Applied composite unique on patients (clinic_id, user_id)")
        except Exception as exc:
            logger.warning("patients clinic/user unique migration skipped: %s", exc)


def ensure_pharmacy_inventory_schema(engine: Engine) -> None:
    """Create pharmacy_inventory table and optional extended columns."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    date_type = "DATE"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"
    if "pharmacy_inventory" not in tables:
        stmt = f"""
            CREATE TABLE pharmacy_inventory (
                id INTEGER PRIMARY KEY{autoinc},
                clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                sku VARCHAR(64) NOT NULL,
                medication_name VARCHAR(255) NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                reorder_level INTEGER NOT NULL DEFAULT 10,
                unit_price_gnf INTEGER NOT NULL DEFAULT 25000,
                batch_number VARCHAR(64),
                expiry_date {date_type},
                supplier VARCHAR(128),
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created pharmacy_inventory table")
        except Exception as exc:
            logger.warning("pharmacy_inventory migration failed: %s", exc)
        return

    cols = {c["name"] for c in insp.get_columns("pharmacy_inventory")}
    for col, ddl in (
        ("batch_number", f"ALTER TABLE pharmacy_inventory ADD COLUMN batch_number VARCHAR(64)"),
        ("expiry_date", f"ALTER TABLE pharmacy_inventory ADD COLUMN expiry_date {date_type}"),
        ("supplier", f"ALTER TABLE pharmacy_inventory ADD COLUMN supplier VARCHAR(128)"),
        ("purchase_price_gnf", "ALTER TABLE pharmacy_inventory ADD COLUMN purchase_price_gnf INTEGER"),
    ):
        if col not in cols:
            try:
                with engine.begin() as conn:
                    conn.execute(text(ddl))
                logger.info("Added pharmacy_inventory.%s", col)
            except Exception as exc:
                logger.warning("pharmacy_inventory.%s migration skipped: %s", col, exc)


def ensure_clinic_charge_payments_schema(engine: Engine) -> None:
    """clinic_charges.paid_amount_gnf + clinic_charge_payments table."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"

    if "clinic_charges" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("clinic_charges")}
        if "paid_amount_gnf" not in cols:
            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE clinic_charges ADD COLUMN paid_amount_gnf INTEGER NOT NULL DEFAULT 0"))
                logger.info("Added clinic_charges.paid_amount_gnf")
            except Exception as exc:
                logger.warning("clinic_charges.paid_amount_gnf migration skipped: %s", exc)

    if "clinic_charge_payments" not in insp.get_table_names():
        stmt = f"""
            CREATE TABLE clinic_charge_payments (
                id INTEGER PRIMARY KEY{autoinc},
                charge_id INTEGER NOT NULL REFERENCES clinic_charges(id),
                amount_gnf INTEGER NOT NULL,
                payment_method VARCHAR(32) NOT NULL,
                reference VARCHAR(128),
                recorded_by_user_id INTEGER REFERENCES users(id),
                created_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created clinic_charge_payments table")
        except Exception as exc:
            logger.warning("clinic_charge_payments migration failed: %s", exc)


def ensure_email_verification_schema(engine: Engine) -> None:
    """users.email_verified_at + email_verification_tokens (Railway create_all gap)."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"

    if "users" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("users")}
        if "email_verified_at" not in cols:
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN email_verified_at {datetime_type}"))
                    conn.execute(text("UPDATE users SET email_verified_at = CURRENT_TIMESTAMP WHERE email_verified_at IS NULL"))
                logger.info("Added users.email_verified_at and backfilled existing accounts")
            except Exception as exc:
                logger.warning("email_verified_at migration skipped: %s", exc)

    if "email_verification_tokens" not in insp.get_table_names():
        stmt = f"""
            CREATE TABLE email_verification_tokens (
                id INTEGER PRIMARY KEY{autoinc},
                user_id INTEGER NOT NULL REFERENCES users(id),
                token_hash VARCHAR(128) NOT NULL UNIQUE,
                expires_at {datetime_type} NOT NULL,
                used_at {datetime_type},
                created_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created email_verification_tokens table")
        except Exception as exc:
            logger.warning("email_verification_tokens migration failed: %s", exc)


def ensure_must_change_password_schema(engine: Engine) -> None:
    """users.must_change_password — required for clinic staff temp password flow."""
    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("users")}
    if "must_change_password" in cols:
        return
    dialect = engine.dialect.name
    bool_type = "BOOLEAN" if dialect == "postgresql" else "BOOLEAN"
    default = "FALSE" if dialect == "postgresql" else "0"
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    f"ALTER TABLE users ADD COLUMN must_change_password {bool_type} NOT NULL DEFAULT {default}"
                )
            )
        logger.info("Added users.must_change_password")
    except Exception as exc:
        logger.warning("must_change_password migration skipped: %s", exc)
    try:
        with engine.begin() as conn:
            conn.execute(text("UPDATE users SET must_change_password = FALSE WHERE must_change_password = TRUE"))
        logger.info("Cleared must_change_password for all existing users")
    except Exception as exc:
        logger.warning("must_change_password clear skipped: %s", exc)


def ensure_clinical_modules_schema(engine: Engine) -> None:
    """PEV, hospitalization, nutrition extensions + nursing_procedures table."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    date_type = "DATE" if dialect == "postgresql" else "DATE"
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"
    bool_type = "BOOLEAN" if dialect == "postgresql" else "BOOLEAN"

    tables = insp.get_table_names()

    if "immunization_records" in tables:
        cols = {c["name"] for c in insp.get_columns("immunization_records")}
        additions = {
            "dose_number": "INTEGER",
            "next_appointment_date": date_type,
            "vaccinator_name": "VARCHAR(128)",
            "vaccine_expiry_date": date_type,
            "injection_site": "VARCHAR(64)",
            "vaccination_strategy": "VARCHAR(32)",
            "age_at_vaccination_months": "INTEGER",
            "age_at_vaccination_days": "INTEGER",
            "aefi_notes": "TEXT",
        }
        for col, col_type in additions.items():
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE immunization_records ADD COLUMN {col} {col_type}"))
                    logger.info("Added immunization_records.%s", col)
                except Exception as exc:
                    logger.warning("immunization_records.%s migration skipped: %s", col, exc)

    if "admissions" in tables:
        cols = {c["name"] for c in insp.get_columns("admissions")}
        for col, col_type in (
            ("outcome", "VARCHAR(64)"),
            ("attending_clinician_user_id", "INTEGER"),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE admissions ADD COLUMN {col} {col_type}"))
                    logger.info("Added admissions.%s", col)
                except Exception as exc:
                    logger.warning("admissions.%s migration skipped: %s", col, exc)

    if "nutrition_assessments" in tables:
        cols = {c["name"] for c in insp.get_columns("nutrition_assessments")}
        for col, col_type in (
            ("nutritional_diagnosis", "TEXT"),
            ("is_follow_up", f"{bool_type} DEFAULT FALSE"),
            ("follow_up_date", date_type),
            ("recommendations", "TEXT"),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE nutrition_assessments ADD COLUMN {col} {col_type}"))
                    logger.info("Added nutrition_assessments.%s", col)
                except Exception as exc:
                    logger.warning("nutrition_assessments.%s migration skipped: %s", col, exc)

    if "nursing_procedures" not in tables:
        stmt = f"""
            CREATE TABLE nursing_procedures (
                id INTEGER PRIMARY KEY{autoinc},
                clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                procedure_type VARCHAR(32) NOT NULL,
                procedure_date {date_type} NOT NULL,
                procedure_time VARCHAR(8),
                nurse_user_id INTEGER REFERENCES users(id),
                nurse_name VARCHAR(128),
                notes TEXT,
                created_at {datetime_type} NOT NULL,
                deleted_at {datetime_type}
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created nursing_procedures table")
        except Exception as exc:
            logger.warning("nursing_procedures migration failed: %s", exc)
    elif "nursing_procedures" in tables:
        cols = {c["name"] for c in insp.get_columns("nursing_procedures")}
        if "procedure_time" not in cols:
            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE nursing_procedures ADD COLUMN procedure_time VARCHAR(8)"))
                logger.info("Added nursing_procedures.procedure_time")
            except Exception as exc:
                logger.warning("nursing_procedures.procedure_time migration skipped: %s", exc)


def ensure_patient_intake_fields(engine: Engine) -> None:
    """Reception intake — mother name, profession, quartier, visit destination."""
    insp = inspect(engine)
    if "patients" not in insp.get_table_names():
        return
    cols = {c["name"] for c in insp.get_columns("patients")}
    for col, col_type in (
        ("mother_name", "VARCHAR(255)"),
        ("profession", "VARCHAR(128)"),
        ("quartier", "VARCHAR(255)"),
        ("visit_destination", "VARCHAR(255)"),
    ):
        if col not in cols:
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE patients ADD COLUMN {col} {col_type}"))
                logger.info("Added patients.%s", col)
            except Exception as exc:
                logger.warning("patients.%s migration skipped: %s", col, exc)


def ensure_doctor_medicine_deliveries_table(engine: Engine) -> None:
    insp = inspect(engine)
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"
    if "doctor_medicine_deliveries" in insp.get_table_names():
        return
    stmt = f"""
        CREATE TABLE doctor_medicine_deliveries (
            id INTEGER PRIMARY KEY{autoinc},
            clinic_id INTEGER NOT NULL REFERENCES clinics(id),
            patient_id INTEGER REFERENCES patients(id),
            patient_name VARCHAR(255) NOT NULL,
            medicine_name VARCHAR(255) NOT NULL,
            quantity INTEGER NOT NULL DEFAULT 1,
            doctor_name VARCHAR(255) NOT NULL,
            reason TEXT,
            source VARCHAR(32) NOT NULL DEFAULT 'doctor_office',
            delivered_at {datetime_type} NOT NULL,
            recorded_by_user_id INTEGER REFERENCES users(id),
            created_at {datetime_type} NOT NULL,
            deleted_at {datetime_type}
        )
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(stmt))
        logger.info("Created doctor_medicine_deliveries table")
    except Exception as exc:
        logger.warning("doctor_medicine_deliveries migration failed: %s", exc)


def ensure_clinic_lab_tests_table(engine: Engine) -> None:
    """Per-clinic laboratory catalog with editable tariff fields."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"
    if "clinic_lab_tests" in insp.get_table_names():
        return
    stmt = f"""
        CREATE TABLE clinic_lab_tests (
            id INTEGER PRIMARY KEY{autoinc},
            clinic_id INTEGER NOT NULL REFERENCES clinics(id),
            code VARCHAR(64) NOT NULL,
            name VARCHAR(255) NOT NULL,
            category VARCHAR(64) NOT NULL,
            category_label VARCHAR(128) NOT NULL,
            price_gnf INTEGER,
            sort_order INTEGER NOT NULL DEFAULT 0,
            active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at {datetime_type} NOT NULL,
            updated_at {datetime_type} NOT NULL,
            UNIQUE (clinic_id, code)
        )
    """
    try:
        with engine.begin() as conn:
            conn.execute(text(stmt))
            conn.execute(text("CREATE INDEX ix_clinic_lab_tests_clinic_id ON clinic_lab_tests (clinic_id)"))
            conn.execute(text("CREATE INDEX ix_clinic_lab_tests_category ON clinic_lab_tests (category)"))
        logger.info("Created clinic_lab_tests table")
    except Exception as exc:
        logger.warning("clinic_lab_tests migration failed: %s", exc)


def ensure_reception_his_schema(engine: Engine) -> None:
    """Reception HIS — extended patient dossier, admissions, invoices, refunds."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    autoinc = "" if dialect == "sqlite" else " GENERATED BY DEFAULT AS IDENTITY"

    if "patients" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("patients")}
        patient_cols = (
            ("patient_number", "VARCHAR(32)"),
            ("qr_token", "VARCHAR(64)"),
            ("photo_url", "TEXT"),
            ("phone_secondary", "VARCHAR(32)"),
            ("email", "VARCHAR(255)"),
            ("commune", "VARCHAR(128)"),
            ("city", "VARCHAR(128)"),
            ("region", "VARCHAR(128)"),
            ("country", "VARCHAR(128)"),
            ("place_of_birth", "VARCHAR(255)"),
            ("nationality", "VARCHAR(128)"),
            ("marital_status", "VARCHAR(64)"),
            ("preferred_language", "VARCHAR(64)"),
            ("emergency_contact_json", "TEXT"),
            ("payer_json", "TEXT"),
            ("mother_first_name", "VARCHAR(128)"),
            ("mother_last_name", "VARCHAR(128)"),
            ("is_newborn", "BOOLEAN DEFAULT FALSE"),
            ("registration_date", "DATE"),
            ("date_of_birth_precision", "VARCHAR(16) DEFAULT 'full'"),
        )
        for col, col_type in patient_cols:
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE patients ADD COLUMN {col} {col_type}"))
                    logger.info("Added patients.%s", col)
                except Exception as exc:
                    logger.warning("patients.%s migration skipped: %s", col, exc)

    if "admissions" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("admissions")}
        for col, col_type in (
            ("department", "VARCHAR(128)"),
            ("admission_type", "VARCHAR(32)"),
            ("services_json", "TEXT"),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE admissions ADD COLUMN {col} {col_type}"))
                    logger.info("Added admissions.%s", col)
                except Exception as exc:
                    logger.warning("admissions.%s migration skipped: %s", col, exc)

    if "invoices" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("invoices")}
        for col, col_type in (
            ("department", "VARCHAR(128)"),
            ("subtotal_amount_gnf", "INTEGER DEFAULT 0"),
            ("exemption_percent", "INTEGER DEFAULT 0"),
            ("exemption_amount_gnf", "INTEGER DEFAULT 0"),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE invoices ADD COLUMN {col} {col_type}"))
                    logger.info("Added invoices.%s", col)
                except Exception as exc:
                    logger.warning("invoices.%s migration skipped: %s", col, exc)

    if "clinic_charges" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("clinic_charges")}
        for col, col_type in (
            ("subtotal_amount_gnf", "INTEGER"),
            ("exemption_percent", "INTEGER DEFAULT 0"),
            ("exemption_amount_gnf", "INTEGER DEFAULT 0"),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE clinic_charges ADD COLUMN {col} {col_type}"))
                    logger.info("Added clinic_charges.%s", col)
                except Exception as exc:
                    logger.warning("clinic_charges.%s migration skipped: %s", col, exc)

    if "clinic_refunds" not in insp.get_table_names():
        stmt = f"""
            CREATE TABLE clinic_refunds (
                id INTEGER PRIMARY KEY{autoinc},
                clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                invoice_id INTEGER NOT NULL REFERENCES invoices(id),
                refund_number VARCHAR(32) NOT NULL UNIQUE,
                original_amount_paid_gnf INTEGER NOT NULL DEFAULT 0,
                service_paid_for TEXT,
                amount_consumed_gnf INTEGER NOT NULL DEFAULT 0,
                refund_amount_gnf INTEGER NOT NULL DEFAULT 0,
                reason VARCHAR(32) NOT NULL,
                reason_notes TEXT,
                recipient_name VARCHAR(255),
                recipient_relationship VARCHAR(128),
                recipient_phone VARCHAR(32),
                refund_method VARCHAR(32),
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                approved_by_user_id INTEGER REFERENCES users(id),
                paid_by_user_id INTEGER REFERENCES users(id),
                approved_at {datetime_type},
                paid_at {datetime_type},
                created_by_user_id INTEGER REFERENCES users(id),
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created clinic_refunds table")
        except Exception as exc:
            logger.warning("clinic_refunds migration failed: %s", exc)

    if "clinic_service_requests" not in insp.get_table_names():
        stmt = f"""
            CREATE TABLE clinic_service_requests (
                id INTEGER PRIMARY KEY{autoinc},
                clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                admission_id INTEGER REFERENCES admissions(id),
                request_number VARCHAR(32) NOT NULL UNIQUE,
                service_category VARCHAR(32) NOT NULL,
                service_name VARCHAR(255) NOT NULL,
                department VARCHAR(128),
                catalog_code VARCHAR(64),
                charge_type VARCHAR(64),
                unit_price_gnf INTEGER,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                notes TEXT,
                created_by_user_id INTEGER REFERENCES users(id),
                updated_by_user_id INTEGER REFERENCES users(id),
                created_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created clinic_service_requests table")
        except Exception as exc:
            logger.warning("clinic_service_requests migration failed: %s", exc)

    if "clinic_service_requests" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("clinic_service_requests")}
        for col, col_type in (
            ("catalog_code", "VARCHAR(64)"),
            ("charge_type", "VARCHAR(64)"),
            ("unit_price_gnf", "INTEGER"),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(
                            text(f"ALTER TABLE clinic_service_requests ADD COLUMN {col} {col_type}")
                        )
                    logger.info("Added clinic_service_requests.%s", col)
                except Exception as exc:
                    logger.warning("clinic_service_requests.%s migration skipped: %s", col, exc)

    if "admissions" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("admissions")}
        for col, col_type in (
            ("specialty_code", "VARCHAR(64)"),
            ("specialty_other", "VARCHAR(255)"),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE admissions ADD COLUMN {col} {col_type}"))
                    logger.info("Added admissions.%s", col)
                except Exception as exc:
                    logger.warning("admissions.%s migration skipped: %s", col, exc)

    if "patient_medical_records" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("patient_medical_records")}
        if "last_specialty" not in cols:
            try:
                with engine.begin() as conn:
                    conn.execute(text("ALTER TABLE patient_medical_records ADD COLUMN last_specialty VARCHAR(255)"))
                logger.info("Added patient_medical_records.last_specialty")
            except Exception as exc:
                logger.warning("patient_medical_records.last_specialty migration skipped: %s", exc)

    if "consultations" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("consultations")}
        for col, col_type in (
            ("medical_history", "TEXT"),
            ("surgical_history", "TEXT"),
            ("gyneco_history", "TEXT"),
            ("allergies", "TEXT"),
            ("current_treatments", "TEXT"),
            ("observations", "TEXT"),
            ("target_specialty_code", "VARCHAR(64)"),
            ("target_specialty_other", "VARCHAR(255)"),
            ("hospitalized_vitals", "TEXT"),
            ("post_op_report", "TEXT"),
            ("discharge_summary_text", "TEXT"),
            ("discharge_authorization", "TEXT"),
            ("discharge_against_advice", "TEXT"),
            ("prescription_text", "TEXT"),
            ("discharge_form_json", "TEXT"),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE consultations ADD COLUMN {col} {col_type}"))
                    logger.info("Added consultations.%s", col)
                except Exception as exc:
                    logger.warning("consultations.%s migration skipped: %s", col, exc)


def run_alembic_upgrade_head(*, fail_closed: bool | None = None) -> None:
    """Apply Alembic migrations on startup (Railway may rely on this path)."""
    import os

    if fail_closed is None:
        env = (os.getenv("ENVIRONMENT") or "").strip().lower()
        fail_closed = env in {"production", "staging", "clinic-node", "clinic_node"} or bool(
            (os.getenv("RAILWAY_ENVIRONMENT") or "").strip()
        )
    try:
        from alembic.config import Config
        from alembic import command

        cfg = Config("alembic.ini")
        command.upgrade(cfg, "head")
        logger.info("Alembic upgrade head completed on startup")
    except Exception as exc:
        logger.exception("Alembic upgrade on startup failed: %s", exc)
        if fail_closed:
            raise RuntimeError(
                "Alembic upgrade head failed — refusing to start with incompatible schema: "
                f"{exc}"
            ) from exc
        logger.warning("Alembic upgrade failed (non-deployed); fallback ensure_* may apply: %s", exc)


def ensure_nurse_assessment_schema(engine: Engine) -> None:
    """Nurse triage assessments and extended vital signs columns."""
    insp = inspect(engine)
    dialect = engine.dialect.name
    datetime_type = "TIMESTAMP" if dialect == "postgresql" else "DATETIME"
    float_type = "DOUBLE PRECISION" if dialect == "postgresql" else "FLOAT"
    autoinc = " AUTOINCREMENT" if dialect == "sqlite" else ""

    if "patient_vital_signs" in insp.get_table_names():
        cols = {c["name"] for c in insp.get_columns("patient_vital_signs")}
        for col, col_type in (
            ("respiratory_rate", "INTEGER"),
            ("bmi", float_type),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE patient_vital_signs ADD COLUMN {col} {col_type}"))
                    logger.info("Added patient_vital_signs.%s", col)
                except Exception as exc:
                    logger.warning("patient_vital_signs.%s migration skipped: %s", col, exc)

    if "nurse_assessments" not in insp.get_table_names():
        stmt = f"""
            CREATE TABLE nurse_assessments (
                id INTEGER PRIMARY KEY{autoinc},
                clinic_id INTEGER NOT NULL REFERENCES clinics(id),
                patient_id INTEGER NOT NULL REFERENCES patients(id),
                admission_id INTEGER REFERENCES admissions(id),
                appointment_id INTEGER REFERENCES rendezvous(id),
                consultation_id INTEGER REFERENCES consultations(id),
                nurse_user_id INTEGER REFERENCES users(id),
                nurse_name VARCHAR(128),
                temperature_c {float_type},
                bp_systolic INTEGER,
                bp_diastolic INTEGER,
                heart_rate INTEGER,
                respiratory_rate INTEGER,
                height_cm {float_type},
                weight_kg {float_type},
                bmi {float_type},
                vitals_observations TEXT,
                reason_for_consultation TEXT,
                history_of_present_illness TEXT,
                medical_history TEXT,
                surgical_history TEXT,
                gynecological_history TEXT,
                allergies TEXT,
                current_treatments TEXT,
                hospitalized_daily_vitals TEXT,
                prescription TEXT,
                nurse_notes TEXT,
                recorded_at {datetime_type} NOT NULL,
                updated_at {datetime_type} NOT NULL,
                deleted_at {datetime_type}
            )
        """
        try:
            with engine.begin() as conn:
                conn.execute(text(stmt))
            logger.info("Created nurse_assessments table")
        except Exception as exc:
            logger.warning("nurse_assessments migration failed: %s", exc)
    else:
        cols = {c["name"] for c in insp.get_columns("nurse_assessments")}
        for col, col_type in (
            ("hospitalized_daily_vitals", "TEXT"),
            ("prescription", "TEXT"),
        ):
            if col not in cols:
                try:
                    with engine.begin() as conn:
                        conn.execute(text(f"ALTER TABLE nurse_assessments ADD COLUMN {col} {col_type}"))
                    logger.info("Added nurse_assessments.%s", col)
                except Exception as exc:
                    logger.warning("nurse_assessments.%s migration skipped: %s", col, exc)


def ensure_lab_result_reference_range_text(engine: Engine) -> None:
    """Hémogramme templates exceed VARCHAR(255) for combined reference ranges."""
    insp = inspect(engine)
    if "lab_results" not in insp.get_table_names():
        return
    dialect = engine.dialect.name
    if dialect != "postgresql":
        return
    try:
        col = next(c for c in insp.get_columns("lab_results") if c["name"] == "reference_range")
        col_type = str(col.get("type", "")).upper()
        if "TEXT" in col_type or "CHARACTER VARYING" not in col_type and "VARCHAR" not in col_type:
            return
    except StopIteration:
        return
    try:
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE lab_results ALTER COLUMN reference_range TYPE TEXT"))
        logger.info("Widened lab_results.reference_range to TEXT")
    except Exception as exc:
        logger.warning("lab_results.reference_range migration skipped: %s", exc)


def ensure_clinic_node_ops_schema(engine: Engine) -> None:
    """Clinic Node ops schema widen + additive columns for production offline V1."""
    insp = inspect(engine)
    tables = set(insp.get_table_names())
    dialect = engine.dialect.name

    if "clinic_node_heartbeats" in tables and dialect == "postgresql":
        cols = {c["name"]: c for c in insp.get_columns("clinic_node_heartbeats")}
        for col_name in ("disk_free_bytes", "disk_total_bytes"):
            col = cols.get(col_name)
            if not col:
                continue
            col_type = str(col.get("type", "")).upper()
            if "BIGINT" in col_type or "BIGINTEGER" in col_type:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(
                        text(f"ALTER TABLE clinic_node_heartbeats ALTER COLUMN {col_name} TYPE BIGINT")
                    )
                logger.info("Widened clinic_node_heartbeats.%s to BIGINT", col_name)
            except Exception as exc:
                logger.warning("clinic_node_heartbeats.%s widen skipped: %s", col_name, exc)

    # Additive columns on sync_outbox_events
    if "sync_outbox_events" in tables:
        cols = {c["name"] for c in insp.get_columns("sync_outbox_events")}
        additions = [
            ("client_request_id", "VARCHAR(64)"),
            ("record_version", "INTEGER DEFAULT 1"),
            ("attempt_count", "INTEGER DEFAULT 0"),
            ("next_retry_at", "TIMESTAMP"),
            ("last_error", "TEXT"),
            ("status", "VARCHAR(32) DEFAULT 'pending'"),
            ("updated_at", "TIMESTAMP"),
        ]
        for col, col_type in additions:
            if col in cols:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE sync_outbox_events ADD COLUMN {col} {col_type}"))
                logger.info("Added sync_outbox_events.%s", col)
            except Exception as exc:
                logger.warning("sync_outbox_events.%s skipped: %s", col, exc)
        # Backfill status from acked_at
        try:
            with engine.begin() as conn:
                conn.execute(
                    text(
                        "UPDATE sync_outbox_events SET status='acked' "
                        "WHERE acked_at IS NOT NULL AND (status IS NULL OR status='pending')"
                    )
                )
        except Exception as exc:
            logger.warning("sync_outbox status backfill skipped: %s", exc)

    if "clinic_node_licenses" in tables:
        cols = {c["name"] for c in insp.get_columns("clinic_node_licenses")}
        for col, col_type in (
            ("signature", "VARCHAR(128) DEFAULT ''"),
            ("activated_at", "TIMESTAMP"),
            ("last_validated_at", "TIMESTAMP"),
        ):
            if col in cols:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE clinic_node_licenses ADD COLUMN {col} {col_type}"))
                logger.info("Added clinic_node_licenses.%s", col)
            except Exception as exc:
                logger.warning("clinic_node_licenses.%s skipped: %s", col, exc)

    if "sync_conflicts" in tables:
        cols = {c["name"] for c in insp.get_columns("sync_conflicts")}
        for col, col_type in (
            ("local_version", "INTEGER"),
            ("remote_version", "INTEGER"),
            ("merged_json", "TEXT"),
            ("resolution_policy", "VARCHAR(32)"),
            ("resolved_by_user_id", "INTEGER"),
        ):
            if col in cols:
                continue
            try:
                with engine.begin() as conn:
                    conn.execute(text(f"ALTER TABLE sync_conflicts ADD COLUMN {col} {col_type}"))
                logger.info("Added sync_conflicts.%s", col)
            except Exception as exc:
                logger.warning("sync_conflicts.%s skipped: %s", col, exc)

