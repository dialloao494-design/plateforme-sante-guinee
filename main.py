from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal
import models
from routers import patient, patient_record, rendezvous, doctor, auth, teleconsultation, notifications, messages
from routers import users, appointments, doctor_dashboard, ws, clinical, medical_history, hospitalization
from routers import unified_billing, discharge, radiology, reminders, clinical_reports, platform, platform_setup
from routers import nutrition, immunization, nursing_care, visit_workflow, clinical_phase2, lab_phase2, pharmacy_phase2, reception_his, nurse_assessment
from security import hash_password, verify_password
from services.user_provisioning import register_public_user
import os
import logging

from core.settings import get_settings
from core.logging_config import configure_logging
from core.monitoring import init_sentry

_settings = get_settings()
try:
    _settings.enforce_production_boot()
except RuntimeError as _boot_exc:
    logging.getLogger(__name__).critical("Production boot guard rejected startup: %s", _boot_exc)
    raise SystemExit(1) from _boot_exc

configure_logging(level=_settings.log_level, log_format=_settings.log_format)
init_sentry()
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Healthcare Platform API",
    description="Comprehensive healthcare appointment and payment API",
    version="1.0.0",
    docs_url="/docs" if _settings.docs_enabled else None,
    redoc_url="/redoc" if _settings.docs_enabled else None,
    openapi_url="/openapi.json" if _settings.docs_enabled else None,
)

# CORS — applied before routers are included.
# Development origins use http:// (local only), production must be HTTPS.
from core.frontend_url import (
    CANONICAL_FRONTEND_URL,
    LEGACY_FRONTEND_HOSTS,
    resolve_frontend_url,
)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
    # Canonical Vercel production project (GitHub-connected)
    CANONICAL_FRONTEND_URL,
]

for part in (os.getenv("CORS_ORIGINS", "") or "").split(","):
    part = part.strip().rstrip("/")
    if not part:
        continue
    host = part.replace("https://", "").replace("http://", "").split("/")[0].lower()
    if host in LEGACY_FRONTEND_HOSTS:
        continue
    if part not in origins:
        origins.append(part)

# Effective FRONTEND_URL only (legacy seven-rust host is remapped away).
_fe = resolve_frontend_url(allow_localhost_fallback=False)
if _fe and _fe not in origins:
    origins.append(_fe)

# CORS: strict in production; LAN/Vercel regex only in dev/staging.
from services.network_dev import COMBINED_DEV_CORS_REGEX, format_lan_urls

_environment = _settings.environment
_lan_dev = os.getenv("ENABLE_LAN_DEV", "").lower() in ("1", "true", "yes")
_tunnel_test = os.getenv("ENABLE_TUNNEL_TEST", "").lower() in ("1", "true", "yes")
_debug = _settings.debug
_is_production = _settings.is_production
_is_deployed = _settings.is_deployed

if _is_deployed:
    cors_origin_regex = None
    cors_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_headers = ["Authorization", "Content-Type", "Accept"]
else:
    from services.network_dev import TUNNEL_ORIGIN_REGEX

    if _tunnel_test:
        cors_origin_regex = TUNNEL_ORIGIN_REGEX
    elif _lan_dev or _debug:
        cors_origin_regex = COMBINED_DEV_CORS_REGEX
    else:
        cors_origin_regex = r"^https://.*\.vercel\.app$"
    cors_methods = ["*"]
    cors_headers = ["*"]

_cors_kwargs = dict(
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=cors_methods,
    allow_headers=cors_headers,
)
if cors_origin_regex:
    _cors_kwargs["allow_origin_regex"] = cors_origin_regex
app.add_middleware(CORSMiddleware, **_cors_kwargs)


@app.middleware("http")
async def low_bandwidth_cache_headers(request, call_next):
    """Short private cache for semi-static GET endpoints (clinic LAN / 3G)."""
    response = await call_next(request)
    if request.method != "GET":
        return response
    path = request.url.path.rstrip("/") or "/"
    if path.endswith("/clinical/immunization/schedule") or path.endswith("/clinical/workflow/departments"):
        response.headers.setdefault("Cache-Control", "private, max-age=3600")
    elif path == "/health":
        response.headers.setdefault("Cache-Control", "public, max-age=60")
    return response

# Rate limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from core.limiter import limiter
from core.security_headers import SecurityHeadersMiddleware

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

# Trust Railway's HTTPS proxy so that request.url.scheme is 'https'
# when Railway terminates TLS and forwards requests to the app over HTTP internally.
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

_allowed_hosts = _settings.resolve_allowed_hosts()
_trusted_proxy_hosts = _settings.resolve_trusted_proxy_hosts()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts=_trusted_proxy_hosts)

# Clinical attachments are never served from a public static mount.
# Legacy /uploads/* URLs are explicitly blocked (defense in depth).
@app.api_route("/uploads/{path:path}", methods=["GET", "HEAD"], include_in_schema=False)
def block_legacy_public_uploads(path: str):
    raise HTTPException(status_code=404, detail="Not found")


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def ensure_dev_test_user():
    """Create or repair a default development login user and its patient profile."""
    db = SessionLocal()
    email = "test@test.com"
    plain_password = "Test123!"

    try:
        user = db.query(models.User).filter(models.User.email == email).first()

        if not user:
            provisioned = register_public_user(
                db,
                email=email,
                password=plain_password,
                role="patient",
            )
            user = provisioned.user
            logger.info("Seeded development test user: %s", email)
        else:
            update_required = False

            try:
                password_ok = verify_password(plain_password, user.hashed_password)
            except Exception:
                password_ok = False

            if not password_ok:
                user.hashed_password = hash_password(plain_password)
                update_required = True

            if user.role != "patient":
                user.role = "patient"
                update_required = True

            if update_required:
                db.commit()
                db.refresh(user)
                logger.info("Updated development test user credentials/role: %s", email)
            else:
                logger.info("Development test user already valid: %s", email)

        # Ensure the dev user has a linked Patient profile so payment endpoints work
        patient_profile = db.query(models.Patient).filter(
            models.Patient.user_id == user.id
        ).first()
        if not patient_profile:
            patient_profile = models.Patient(
                user_id=user.id,
                first_name="Test",
                last_name="Dev",
                age=30,
                gender="other",
            )
            db.add(patient_profile)
            db.commit()
            logger.info("Created patient profile for dev test user: %s", email)

    except Exception as exc:
        db.rollback()
        logger.error("Failed to ensure development test user: %s", exc)
    finally:
        db.close()


def _ensure_production_test_user():
    """Idempotently create the optional startup test user (disabled in production)."""
    db = SessionLocal()
    email = "test123@gmail.com"
    plain_password = "Test123!"
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if user is None:
            provisioned = register_public_user(
                db,
                email=email,
                password=plain_password,
                role="patient",
            )
            user = provisioned.user
            logger.info("Production test user created: %s (id=%s)", email, user.id)
        else:
            # Repair password if it doesn't match
            try:
                ok = verify_password(plain_password, user.hashed_password)
            except Exception:
                ok = False
            if not ok:
                user.hashed_password = hash_password(plain_password)
                db.commit()
                logger.info("Production test user password repaired: %s", email)
            else:
                logger.info("Production test user already valid: %s (id=%s)", email, user.id)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to ensure production test user: %s", exc)
        raise
    finally:
        db.close()


# Include routers
app.include_router(patient.router)
app.include_router(patient_record.router)
app.include_router(rendezvous.router)
app.include_router(doctor.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(platform_setup.router)
app.include_router(platform.router)
app.include_router(appointments.router)
app.include_router(teleconsultation.router)
app.include_router(notifications.router)
app.include_router(messages.router)
app.include_router(doctor_dashboard.router)
app.include_router(clinical.router)
app.include_router(medical_history.router)
app.include_router(hospitalization.router)
app.include_router(unified_billing.router)
app.include_router(discharge.router)
app.include_router(radiology.router)
app.include_router(nutrition.router)
app.include_router(immunization.router)
app.include_router(nursing_care.router)
app.include_router(nurse_assessment.router)
app.include_router(clinical_phase2.router)
app.include_router(lab_phase2.router)
app.include_router(pharmacy_phase2.router)
app.include_router(visit_workflow.router)
app.include_router(reminders.router)
app.include_router(clinical_reports.router)
app.include_router(reception_his.router)
app.include_router(ws.router)


# ==========================================
# HEALTH CHECK & MONITORING
# ==========================================

from pydantic import BaseModel

class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    debug: bool
    database: str


@app.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check():
    """
    API Health Check Endpoint
    
    Returns:
    - status: 'ok' if API is healthy
    - version: API version
    - debug: Debug mode status
    - database: Database URL (masked for security)
    
    Use this endpoint for monitoring and uptime checks
    """
    db_url = os.getenv("DATABASE_URL", "sqlite:///./sante.db")
    # Mask sensitive info
    db_url_masked = "***" if "://" in db_url else db_url
    
    return {
        "status": "ok",
        "version": "1.0.0",
        "debug": _settings.debug,
        "database": db_url_masked,
    }


@app.get("/health/email", tags=["Monitoring"])
def health_email():
    """Email channel readiness (SMTP or Resend) — no credentials exposed."""
    from services.email_service import email_config_status

    status_payload = email_config_status()
    return {"status": "ok" if status_payload["configured"] else "not_configured", **status_payload}


def _database_fingerprint() -> dict:
    """Return non-secret DB identity (host + database name) from env + live SQL."""
    from urllib.parse import urlparse

    from sqlalchemy import text

    db_url = os.getenv("DATABASE_URL", "sqlite:///./sante.db")
    parsed = urlparse(db_url)
    host = parsed.hostname or ""
    # Mask only credentials; keep host/db visible for ops identity checks.
    if host and len(host) > 12:
        host_masked = host[:4] + "***" + host[-8:]
    else:
        host_masked = host or "(none)"
    db_name_from_url = (parsed.path or "").lstrip("/") or None

    live = {"current_database": None, "inet_server_addr": None, "server_version": None}
    db = SessionLocal()
    try:
        row = db.execute(
            text(
                "SELECT current_database() AS db, "
                "CAST(inet_server_addr() AS TEXT) AS addr, "
                "current_setting('server_version') AS ver"
            )
        ).mappings().first()
        if row:
            live["current_database"] = row["db"]
            live["inet_server_addr"] = row["addr"]
            live["server_version"] = row["ver"]
    except Exception:
        # SQLite / non-Postgres: fall back to a simple ping.
        db.execute(text("SELECT 1"))
    finally:
        db.close()

    return {
        "dialect": (parsed.scheme or "").split("+")[0] or "unknown",
        "host": host,
        "host_masked": host_masked,
        "port": parsed.port,
        "database_name": live["current_database"] or db_name_from_url,
        "database_name_from_url": db_name_from_url,
        "inet_server_addr": live["inet_server_addr"],
        "server_version": live["server_version"],
    }


@app.get("/health/ready", tags=["Monitoring"])
def health_ready():
    """Readiness: verifies database connectivity (for orchestrators / load balancers)."""
    from sqlalchemy import text

    try:
        db = SessionLocal()
        try:
            db.execute(text("SELECT 1"))
            return {"status": "ready", "database": "ok"}
        finally:
            db.close()
    except Exception as exc:
        logger.error("Readiness check failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database not ready")


@app.get("/health/database", tags=["Monitoring"])
def health_database():
    """
    Non-secret PostgreSQL identity for proving shared production DB.

    Never returns username/password. Safe for dual-frontend verification.
    """
    try:
        fp = _database_fingerprint()
        return {"status": "ok", **fp}
    except Exception as exc:
        logger.error("Database fingerprint failed: %s", exc)
        raise HTTPException(status_code=503, detail="Database identity unavailable")


@app.get("/", tags=["Root"])
def root():
    """API root — docs link only when OpenAPI is enabled."""
    payload = {
        "message": "Healthcare Platform API",
        "version": "1.0.0",
        "health": "/health",
        "ready": "/health/ready",
    }
    if _settings.docs_enabled:
        payload["docs"] = "/docs"
    return payload


# ==========================================
# APP LIFECYCLE EVENTS
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Run on app startup"""
    try:
        from database import engine, Base
        # Import all model modules so their tables are registered on Base
        import models.user, models.patient, models.doctor, models.rendezvous, models.payment, models.availability, models.message, models.notification_event, models.attachment_access_log, models.clinical_note, models.consultation_summary, models.patient_document, models.clinical_audit_log
        import models.clinic, models.clinical_consultation, models.lab_order, models.lab_result, models.prescription, models.pharmacy_order, models.clinic_charge, models.clinic_charge_payment, models.medical_history, models.hospitalization, models.clinical_visit, models.invoice, models.discharge, models.imaging, models.appointment_reminder, models.pharmacy_inventory, models.password_reset_token, models.email_verification_token, models.visit_workflow, models.nutrition, models.immunization, models.nursing_care, models.nurse_assessment  # noqa: F401

        # Local/test environments may bootstrap an empty disposable database.
        # Deployed environments must be controlled by versioned migrations only.
        if not _settings.is_deployed:
            Base.metadata.create_all(bind=engine)
            logger.info("Development database tables verified / created.")

        from database_migrations import (
            ensure_attachment_access_log_table,
            ensure_clinic_charges_table,
            ensure_clinical_audit_clinic_id,
            ensure_clinical_audit_patient_nullable,
            ensure_doctor_geolocation_columns,
            ensure_medical_history_schema,
            ensure_hospitalization_schema,
            ensure_discharge_schema,
            ensure_radiology_schema,
            ensure_reminders_schema,
            ensure_pharmacy_inventory_schema,
            ensure_clinic_charge_payments_schema,
            ensure_patient_user_id_unique,
            ensure_message_attachment_columns,
            ensure_patient_dossier_schema,
            ensure_user_roles_check_constraint,
            normalize_legacy_user_roles,
            ensure_email_verification_schema,
            ensure_must_change_password_schema,
            ensure_clinical_modules_schema,
            ensure_patient_intake_fields,
            ensure_doctor_medicine_deliveries_table,
            ensure_clinic_lab_tests_table,
            ensure_reception_his_schema,
            ensure_nurse_assessment_schema,
            ensure_lab_result_reference_range_text,
            run_alembic_upgrade_head,
        )

        run_alembic_upgrade_head()

        ensure_doctor_geolocation_columns(engine)
        ensure_message_attachment_columns(engine)
        ensure_attachment_access_log_table(engine)
        ensure_patient_dossier_schema(engine)
        ensure_clinic_charges_table(engine)
        ensure_clinical_audit_clinic_id(engine)
        ensure_clinical_audit_patient_nullable(engine)
        ensure_medical_history_schema(engine)
        ensure_hospitalization_schema(engine)
        ensure_discharge_schema(engine)
        ensure_radiology_schema(engine)
        ensure_reminders_schema(engine)
        ensure_pharmacy_inventory_schema(engine)
        ensure_clinic_charge_payments_schema(engine)
        ensure_patient_user_id_unique(engine)
        ensure_user_roles_check_constraint(engine)
        normalize_legacy_user_roles(engine)
        ensure_email_verification_schema(engine)
        ensure_must_change_password_schema(engine)
        ensure_clinical_modules_schema(engine)
        ensure_patient_intake_fields(engine)
        ensure_doctor_medicine_deliveries_table(engine)
        ensure_clinic_lab_tests_table(engine)
        ensure_reception_his_schema(engine)
        ensure_nurse_assessment_schema(engine)
        ensure_lab_result_reference_range_text(engine)

        if _settings.is_deployed:
            from sqlalchemy import inspect

            inspector = inspect(engine)
            required_tables = {
                "users",
                "clinics",
                "patients",
                "doctors",
                "clinical_visits",
                "invoices",
                "clinical_audit_logs",
            }
            missing_tables = sorted(required_tables - set(inspector.get_table_names()))
            user_columns = (
                {column["name"] for column in inspector.get_columns("users")}
                if not missing_tables and "users" in required_tables
                else set()
            )
            missing_user_columns = sorted(
                {"role", "clinic_id", "session_version"} - user_columns
            )
            if missing_tables or missing_user_columns:
                raise RuntimeError(
                    "Database schema is incomplete after migrations: "
                    f"missing_tables={missing_tables}, "
                    f"missing_users_columns={missing_user_columns}"
                )

        from database import SessionLocal
        from services.user_provisioning import bootstrap_initial_admin, bootstrap_platform_owner

        bootstrap_db = SessionLocal()
        try:
            bootstrap_platform_owner(bootstrap_db)
            bootstrap_initial_admin(bootstrap_db)
        finally:
            bootstrap_db.close()
    except Exception as exc:
        logger.exception("Database schema initialization failed")
        if _settings.is_deployed:
            # Never accept traffic with a partially migrated clinical schema.
            raise RuntimeError("Database schema initialization failed") from exc

    # Optional weak test user — disabled by default (set ENABLE_STARTUP_TEST_USER=true to enable)
    if _env_flag("ENABLE_STARTUP_TEST_USER", default=False):
        try:
            _ensure_production_test_user()
        except Exception as exc:
            logger.error("Failed to ensure production test user: %s", exc)
    else:
        logger.info("Startup test user seed skipped (ENABLE_STARTUP_TEST_USER not set).")

    # Pilot accounts — off by default in production (use ENABLE_PILOT_SEED or Docker entrypoint)
    _default_pilot = not _is_production
    if _env_flag("ENABLE_PILOT_SEED", default=_default_pilot):
        try:
            from services.pilot_seed import seed_pilot_accounts

            seed_pilot_accounts()
            from services.clinic_pilot_seed import seed_clinic_pilot_accounts

            seed_clinic_pilot_accounts()
        except Exception as exc:
            logger.error("Failed to seed pilot accounts: %s", exc)
    else:
        logger.info("Pilot seed skipped (ENABLE_PILOT_SEED not set).")

    if _env_flag("ENABLE_DEMO_CLINIC_SEED", default=False):
        try:
            from services.demo_clinic_seed import seed_demo_clinic_data

            seed_demo_clinic_data()
        except Exception as exc:
            logger.error("Failed to seed demo clinic dataset: %s", exc)

    if _env_flag("ENABLE_MEDICAL_HISTORY_SEED", default=False):
        try:
            from database import SessionLocal
            from services.medical_history_seed import seed_medical_history

            db = SessionLocal()
            try:
                seed_medical_history(db)
            finally:
                db.close()
        except Exception as exc:
            logger.error("Failed to seed medical history dataset: %s", exc)

    if _env_flag("ENABLE_STARTUP_SEED", default=False):
        ensure_dev_test_user()
        logger.info("Optional startup seed (dev test user only) completed.")
    else:
        logger.info("Optional startup seed routines skipped (ENABLE_STARTUP_SEED not set).")

    if _env_flag("ENABLE_REMINDER_CRON", default=False):
        import asyncio

        async def _reminder_cron_loop() -> None:
            from services.reminder_service import ReminderService

            while True:
                try:
                    db = SessionLocal()
                    try:
                        sent = ReminderService.process_due_reminders(db)
                        if sent:
                            logger.info("Reminder cron sent %s message(s)", sent)
                    finally:
                        db.close()
                except Exception as exc:
                    logger.error("Reminder cron error: %s", exc)
                await asyncio.sleep(int(os.getenv("REMINDER_CRON_INTERVAL_SEC", "900")))

        asyncio.create_task(_reminder_cron_loop())
        logger.info("Reminder cron enabled (ENABLE_REMINDER_CRON)")

    debug_mode = _settings.debug
    port = os.environ.get("PORT")
    logger.info("Healthcare Platform API startup complete")
    logger.info("OpenAPI docs: %s", "enabled" if _settings.docs_enabled else "disabled")
    logger.info("Debug Mode: %s", debug_mode)
    logger.info("Allowed Hosts: %s", ", ".join(_allowed_hosts))
    logger.info("Bind Port (PORT): %s", port)
    logger.info("Docs Path: %s", "/docs" if _settings.docs_enabled else "(disabled)")
    logger.info("Health Path: /health")
    logger.info("CORS Origins: %s", ", ".join(origins))
    logger.info("CORS Regex: %s", cors_origin_regex or "(disabled — explicit origins only)")
    logger.info("Environment: %s", _environment)
    if _lan_dev or _debug:
        urls = format_lan_urls(
            frontend_port=int(os.getenv("VITE_DEV_PORT", "5173")),
            backend_port=int(os.getenv("PORT", "8000")),
        )
        logger.info("LAN QA — phone frontend: %s", urls["frontend"])
        logger.info("LAN QA — API: %s", urls["backend"])


@app.on_event("shutdown")
async def shutdown_event():
    """Run on app shutdown"""
    logger.info("API shutting down...")


# ==========================================
# ERROR HANDLERS
# ==========================================

from fastapi import Request
from fastapi.exception_handlers import http_exception_handler, request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors without swallowing HTTP or validation errors."""
    if isinstance(exc, HTTPException):
        return await http_exception_handler(request, exc)
    if isinstance(exc, RequestValidationError):
        return await request_validation_exception_handler(request, exc)
    logger.error("Unhandled error: %s", str(exc), exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "data": None,
            "message": "Internal server error. Please try again later.",
            "error_code": "INTERNAL_ERROR"
        }
    )
