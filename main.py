from dotenv import load_dotenv

load_dotenv()

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import SessionLocal
import models
from routers import patient, rendezvous, doctor, auth, payments, teleconsultation, notifications, messages
from routers import users, appointments, doctor_dashboard, ws
from security import hash_password, verify_password
import os
import logging

from core.settings import get_settings
from core.logging_config import configure_logging
from core.monitoring import init_sentry

_settings = get_settings()
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
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "https://localhost:5173",
    "https://127.0.0.1:5173",
    "https://plateforme-sante-guinee-jcny86kfo-dialloa0494-designs-projects.vercel.app",
]

for part in (os.getenv("CORS_ORIGINS", "") or "").split(","):
    part = part.strip()
    if part and part not in origins:
        origins.append(part)

for env_key in ("FRONTEND_URL", "FRONTEND_PRODUCTION_URL"):
    fe = (os.getenv(env_key) or "").strip()
    if fe and fe not in origins:
        origins.append(fe)

# CORS: strict in production; LAN/Vercel regex only in dev/staging.
from services.network_dev import COMBINED_DEV_CORS_REGEX, format_lan_urls

_environment = _settings.environment
_lan_dev = os.getenv("ENABLE_LAN_DEV", "").lower() in ("1", "true", "yes")
_debug = _settings.debug
_is_production = _settings.is_production
_is_deployed = _settings.is_deployed

if _is_deployed:
    cors_origin_regex = None
    cors_methods = ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"]
    cors_headers = ["Authorization", "Content-Type", "Accept"]
else:
    cors_origin_regex = COMBINED_DEV_CORS_REGEX if (_lan_dev or _debug) else r"^https://.*\.vercel\.app$"
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

# Rate limiting
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from core.limiter import limiter

limiter.init_app(app)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Trust Railway's HTTPS proxy so that request.url.scheme is 'https'
# when Railway terminates TLS and forwards requests to the app over HTTP internally.
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

_allowed_hosts = _settings.resolve_allowed_hosts()
app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def ensure_dev_test_user():
    """Create or repair a default development login user and its patient profile."""
    db = SessionLocal()
    email = "test@test.com"
    plain_password = "test123"

    try:
        user = db.query(models.User).filter(models.User.email == email).first()

        if not user:
            user = models.User(
                email=email,
                hashed_password=hash_password(plain_password),
                role="patient",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
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
    """Idempotently create the production test user (test123@gmail.com / 123456)."""
    db = SessionLocal()
    email = "test123@gmail.com"
    plain_password = "123456"
    try:
        user = db.query(models.User).filter(models.User.email == email).first()
        if user is None:
            user = models.User(
                email=email,
                hashed_password=hash_password(plain_password),
                role="patient",
            )
            db.add(user)
            db.commit()
            db.refresh(user)
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
app.include_router(rendezvous.router)
app.include_router(doctor.router)
app.include_router(auth.router)
app.include_router(users.router)
app.include_router(appointments.router)
app.include_router(payments.router)
app.include_router(teleconsultation.router)
app.include_router(notifications.router)
app.include_router(messages.router)
app.include_router(doctor_dashboard.router)
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
    
    payload = {
        "status": "ok",
        "version": "1.0.0",
        "environment": _settings.environment,
        "database": db_url_masked,
    }
    if not _settings.is_deployed:
        payload["debug"] = _settings.debug
    return payload


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
        import models.user, models.patient, models.doctor, models.rendezvous, models.payment, models.availability, models.message, models.notification_event

        # Always create tables if they don't exist (safe / idempotent)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified / created.")

        from database_migrations import ensure_doctor_geolocation_columns

        ensure_doctor_geolocation_columns(engine)
    except Exception as exc:
        logger.error("Failed to create tables: %s", exc)

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

    if _env_flag("ENABLE_STARTUP_SEED", default=False):
        ensure_dev_test_user()
        logger.info("Optional startup seed (dev test user only) completed.")
    else:
        logger.info("Optional startup seed routines skipped (ENABLE_STARTUP_SEED not set).")

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