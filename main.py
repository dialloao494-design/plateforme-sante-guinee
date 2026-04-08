from dotenv import load_dotenv 
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import engine, Base
import models
from routers import patient, rendezvous, doctor, auth, payments, teleconsultation, notifications
from routers import users, appointments
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

# Create tables
Base.metadata.create_all(bind=engine)

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
    debug_mode = os.getenv("DEBUG", "False").lower() == "true"
    logger.info("╔════════════════════════════════════════╗")
    logger.info("║  Healthcare Platform API Starting     ║")
    logger.info("╚════════════════════════════════════════╝")
    logger.info(f"Debug Mode: {debug_mode}")
    logger.info(f"API URL: http://0.0.0.0:{os.getenv('PORT', '8000')}")
    logger.info("Interactive API Docs: http://localhost:8000/docs")
    logger.info("Health Check: http://localhost:8000/health")
    logger.info("Database Tables: Created successfully")
    logger.info("CORS Origins: " + ", ".join(allowed_origins))
    logger.info("Ready to accept requests")


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