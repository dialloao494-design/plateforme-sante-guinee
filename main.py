from dotenv import load_dotenv 
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import SessionLocal
import models
from routers import patient, rendezvous, doctor, auth, payments, teleconsultation, notifications
from routers import users, appointments
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
    description="Comprehensive healthcare appointment and payment system",
    version="1.0.0"
)

# CORS: allow frontend localhost origins for local development
# For production, update allow_origins with your actual domain
allowed_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# Add production domain if specified in env
prod_url = os.getenv("FRONTEND_PRODUCTION_URL")
if prod_url:
    allowed_origins.append(prod_url)

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def seed_demo_doctors():
    db = SessionLocal()
    try:
        doctor_count = db.query(models.Doctor).count()
        if doctor_count > 0:
            return

        demo_doctors = [
            {
                "email": "dr.amu@example.com",
                "password": "Doctor123!",
                "first_name": "Amina",
                "last_name": "Mamadou",
                "specialty": "Pediatrics",
                "location": "Conakry",
                "phone": "+224620000001",
                "photo_url": "https://api.dicebear.com/7.x/female/svg?seed=Amina",
                "consultation_fee": 40000,
            },
            {
                "email": "dr.soulaiman@example.com",
                "password": "Doctor123!",
                "first_name": "Souleymane",
                "last_name": "Diallo",
                "specialty": "General Medicine",
                "location": "Conakry",
                "phone": "+224620000002",
                "photo_url": "https://api.dicebear.com/7.x/male/svg?seed=Souleymane",
                "consultation_fee": 35000,
            },
            {
                "email": "dr.fatou@example.com",
                "password": "Doctor123!",
                "first_name": "Fatou",
                "last_name": "Kaba",
                "specialty": "Dermatology",
                "location": "Kindia",
                "phone": "+224620000003",
                "photo_url": "https://api.dicebear.com/7.x/female/svg?seed=Fatou",
                "consultation_fee": 38000,
            },
        ]

        for doc_data in demo_doctors:
            user = db.query(models.User).filter(models.User.email == doc_data["email"]).first()
            if not user:
                user = models.User(
                    email=doc_data["email"],
                    hashed_password=hash_password(doc_data["password"]),
                    role="doctor",
                )
                db.add(user)
                db.commit()
                db.refresh(user)

            existing_doctor = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
            if existing_doctor:
                continue

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
        logger.info("Demo doctors seeded successfully.")
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
    from database import engine, DATABASE_URL
    # Import all model modules so their tables are registered on Base
    import models.user, models.patient, models.doctor, models.rendezvous, models.payment, models.availability

    # Always create tables if they don't exist (safe / idempotent)
    try:
        from database import Base
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables verified / created.")
    except Exception as exc:
        logger.error("Failed to create tables: %s", exc)

    # Always ensure the production test user exists
    try:
        _ensure_production_test_user()
    except Exception as exc:
        logger.error("Failed to ensure production test user: %s", exc)

    if _env_flag("ENABLE_STARTUP_SEED", default=False):
        seed_demo_doctors()
        seed_test_patient()
        ensure_dev_test_user()
        logger.info("Startup seed routines completed.")
    else:
        logger.info("Optional startup seed routines skipped (ENABLE_STARTUP_SEED not set).")

    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    logger.info("Healthcare Platform API startup complete")
    logger.info("Debug Mode: %s", debug_mode)
    logger.info("API URL: http://0.0.0.0:%s", os.getenv("PORT", "8000"))
    logger.info("Interactive API Docs: http://localhost:8000/docs")
    logger.info("Health Check: http://localhost:8000/health")
    logger.info("CORS Origins: %s", ", ".join(allowed_origins))


@app.on_event("shutdown")
async def shutdown_event():
    """Run on app shutdown"""
    logger.info("API shutting down...")


# ==========================================
# ERROR HANDLERS
# ==========================================

from fastapi import Request
from fastapi.responses import JSONResponse


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected errors"""
    logger.error(f"Unhandled error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "status": "error",
            "data": None,
            "message": "Internal server error. Please try again later.",
            "error_code": "INTERNAL_ERROR"
        }
    )