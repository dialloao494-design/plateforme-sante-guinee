from dotenv import load_dotenv 
load_dotenv()

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from database import SessionLocal
import models
from routers import patient, rendezvous, doctor, auth, payments, teleconsultation, notifications, messages
from routers import users, appointments, doctor_dashboard
from security import hash_password, verify_password
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
title="Healthcare Platform API",
description="Comprehensive healthcare appointment and payment API",
version="1.0.0",
docs_url="/docs",
redoc_url="/redoc",
openapi_url="/openapi.json",
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

# Matches any Vercel preview/production deployment over HTTPS only.
vercel_origin_regex = r"^https://.*\.vercel\.app$"

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=vercel_origin_regex,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Trust Railway's HTTPS proxy so that request.url.scheme is 'https'
# when Railway terminates TLS and forwards requests to the app over HTTP internally.
from starlette.middleware.trustedhost import TrustedHostMiddleware
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

uploads_dir = Path("uploads")
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def seed_demo_doctors():
    """Idempotently ensure demo doctor users + profiles exist (SQLite email compare is case-sensitive)."""
    from sqlalchemy import func

    db = SessionLocal()
    try:
        demo_doctors = [
            {
                "email": "dr.amu@example.com",
                "password": "Doctor123!",
                "first_name": "Amina",
                "last_name": "Barry",
                "specialty": "Pédiatrie",
                "location": "Conakry · Kaloum — Clinique médico-chirurgicale (CMS) Dixinn",
                "phone": "+224 620 00 00 01",
                "photo_url": "https://api.dicebear.com/7.x/female/svg?seed=AminaBarry",
                "consultation_fee": 45000,
            },
            {
                "email": "dr.soulaiman@example.com",
                "password": "Doctor123!",
                "first_name": "Souleymane",
                "last_name": "Diallo",
                "specialty": "Médecine générale",
                "location": "Conakry · Ratoma — Cabinet télésanté & suivi chronique",
                "phone": "+224 620 00 00 02",
                "photo_url": "https://api.dicebear.com/7.x/male/svg?seed=SouleymaneDiallo",
                "consultation_fee": 40000,
            },
            {
                "email": "dr.fatou@example.com",
                "password": "Doctor123!",
                "first_name": "Fatoumata",
                "last_name": "Kaba",
                "specialty": "Dermatologie",
                "location": "Kindia — Centre de santé urbain, consultations hybrides",
                "phone": "+224 620 00 00 03",
                "photo_url": "https://api.dicebear.com/7.x/female/svg?seed=FatoumataKaba",
                "consultation_fee": 42000,
            },
        ]

        for doc_data in demo_doctors:
            email = doc_data["email"].lower().strip()
            plain = doc_data["password"]

            user = db.query(models.User).filter(func.lower(models.User.email) == email).first()
            if not user:
                user = models.User(
                    email=email,
                    hashed_password=hash_password(plain),
                    role="doctor",
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                logger.info("Created demo doctor user: %s", email)
            else:
                changed = False
                if (user.email or "").lower() != email:
                    user.email = email
                    changed = True
                try:
                    password_ok = verify_password(plain, user.hashed_password)
                except Exception:
                    password_ok = False
                if not password_ok:
                    user.hashed_password = hash_password(plain)
                    changed = True
                    logger.info("Reset demo doctor password for: %s", email)
                if user.role != "doctor":
                    user.role = "doctor"
                    changed = True
                if changed:
                    db.commit()
                    db.refresh(user)

            existing_doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
            if not existing_doctor:
                doctor = models.Doctor(
                    user_id=user.id,
                    first_name=doc_data["first_name"],
                    last_name=doc_data["last_name"],
                    specialty=doc_data["specialty"],
                    city=doc_data["location"],
                    phone=doc_data["phone"],
                    photo_url=doc_data["photo_url"],
                    consultation_fee=doc_data["consultation_fee"],
                )
                db.add(doctor)
                db.commit()
                logger.info("Created demo doctor profile for: %s", email)
            else:
                demo_emails = {d["email"].lower().strip() for d in demo_doctors}
                if email in demo_emails:
                    sync_fields = (
                        ("first_name", doc_data["first_name"]),
                        ("last_name", doc_data["last_name"]),
                        ("specialty", doc_data["specialty"]),
                        ("city", doc_data["location"]),
                        ("phone", doc_data["phone"]),
                        ("photo_url", doc_data["photo_url"]),
                        ("consultation_fee", doc_data["consultation_fee"]),
                    )
                    changed = False
                    for attr, value in sync_fields:
                        if getattr(existing_doctor, attr) != value:
                            setattr(existing_doctor, attr, value)
                            changed = True
                    if changed:
                        db.commit()
                        logger.info("Updated demo doctor profile copy for: %s", email)

        logger.info("Demo doctors verified successfully.")
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to seed demo doctors: {exc}")
    finally:
        db.close()


def seed_test_patient():
    db = SessionLocal()
    try:
        patient = db.query(models.Patient).filter(models.Patient.id == 1).first()
        if patient:
            logger.info("Test patient already exists with id=1")
            return

        user = db.query(models.User).filter(models.User.email == "test.patient@example.com").first()
        if not user:
            user = models.User(
                email="test.patient@example.com",
                hashed_password=hash_password("Patient123!"),
                role="patient",
            )
            db.add(user)
            db.commit()
            db.refresh(user)

        test_patient = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
        if not test_patient:
            test_patient = models.Patient(
                id=1,
                user_id=user.id,
                first_name="Test",
                last_name="Patient",
                age=30,
                gender="other",
            )
            db.add(test_patient)
            db.commit()
            db.refresh(test_patient)
            logger.info("Seeded test patient with id=1")
        else:
            logger.info("Test patient profile exists for user %s", user.email)
    except Exception as exc:
        db.rollback()
        logger.error(f"Failed to seed test patient: {exc}")
    finally:
        db.close()


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
        "debug": os.getenv("DEBUG", "False").lower() == "true",
        "database": db_url_masked
    }


@app.get("/", tags=["Root"])
def root():
    """API Root - Redirect to docs"""
    return {
        "message": "Healthcare Platform API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }


# ==========================================
# APP LIFECYCLE EVENTS
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Run on app startup"""
    try:
        from database import engine, Base
        # Import all model modules so their tables are registered on Base
        import models.user, models.patient, models.doctor, models.rendezvous, models.payment, models.availability, models.message

        # Always create tables if they don't exist (safe / idempotent)
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified / created.")
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

    # Always seed demo doctors so the list is never empty
    try:
        seed_demo_doctors()
    except Exception as exc:
        logger.error("Failed to seed demo doctors: %s", exc)

    if _env_flag("ENABLE_DEMO_CLINIC_SEED", default=False):
        try:
            from services.demo_clinic_seed import seed_demo_clinic_data

            seed_demo_clinic_data()
        except Exception as exc:
            logger.error("Failed to seed demo clinic dataset: %s", exc)

    if _env_flag("ENABLE_STARTUP_SEED", default=False):
        seed_test_patient()
        ensure_dev_test_user()
        logger.info("Optional startup seed routines completed.")
    else:
        logger.info("Optional startup seed routines skipped (ENABLE_STARTUP_SEED not set).")

    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    port = os.environ.get("PORT")
    logger.info("Healthcare Platform API startup complete")
    logger.info("Debug Mode: %s", debug_mode)
    logger.info("Bind Port (PORT): %s", port)
    logger.info("Docs Path: /docs")
    logger.info("Health Path: /health")
    logger.info("CORS Origins: %s", ", ".join(origins))
    logger.info("CORS Regex: %s", vercel_origin_regex)


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