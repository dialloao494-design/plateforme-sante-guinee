import logging

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from core.limiter import limiter
from sqlalchemy import func
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from database import get_db
from models.user import User
import models
from schemas.user import UserCreate, UserLogin, UserResponse, Token
from security import (
    get_current_user,
    hash_password,
    verify_password,
    create_access_token,
)
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit(os.getenv("RATE_LIMIT_REGISTER", "5/minute"))
def register(request: Request, user: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user with email, password, and role.
    
    - email: Valid email address (will be stored lowercase)
    - password: Minimum 6 characters
    - role: One of 'patient', 'doctor', 'admin' (defaults to 'patient')
    
    Raises:
    - 409: Email already registered
    - 422: Validation error (invalid email, password, or role format)
    """
    # Check if email already exists (case-insensitive; SQLite compares emails case-sensitively)
    existing_user = db.query(User).filter(func.lower(User.email) == user.email.lower().strip()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user.email}' is already registered. Try logging in or use another email.",
        )

    # Hash password with bcrypt
    hashed_pw = hash_password(user.password)
    new_user = User(
        email=user.email.lower().strip(),
        hashed_password=hashed_pw,
        role=user.role,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        # Auto-create a Patient profile for every patient-role user so that
        # appointment booking and payment endpoints can always find a linked profile.
        if new_user.role == "patient":
            existing_profile = db.query(models.Patient).filter(
                models.Patient.user_id == new_user.id
            ).first()
            if not existing_profile:
                patient_profile = models.Patient(
                    user_id=new_user.id,
                    first_name=None,
                    last_name=None,
                    age=None,
                    gender=None,
                )
                db.add(patient_profile)
                db.commit()

        if new_user.role == "doctor":
            existing_doctor_profile = db.query(models.Doctor).filter(
                models.Doctor.user_id == new_user.id
            ).first()
            if not existing_doctor_profile:
                doctor_profile = models.Doctor(
                    user_id=new_user.id,
                    first_name="Doctor",
                    last_name=f"User{new_user.id}",
                    specialty="Médecine générale",
                    city="Conakry · Kaloum",
                    phone="000000000",
                    photo_url=None,
                    consultation_fee=0.0,
                )
                db.add(doctor_profile)
                db.commit()

        if new_user is None or new_user.id is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="User creation failed unexpectedly.",
            )
        doctor_id = None
        if new_user.role == "doctor":
            doc = db.query(models.Doctor).filter(models.Doctor.user_id == new_user.id).first()
            if doc:
                doctor_id = doc.id
        return UserResponse(id=new_user.id, email=new_user.email, role=new_user.role, doctor_id=doctor_id)
    except IntegrityError as e:
        db.rollback()
        if "email" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creating user. Please try again.",
        )


def authenticate_user(email: str, password: str, db: Session, attempt_limit: int = 1000):
    """
    Authenticate user by email and password.
    
    Returns User object if credentials are valid, None otherwise.
    Uses constant-time password comparison to prevent timing attacks.
    """
    # Normalize email input; match case-insensitively for SQLite and legacy rows
    email = email.lower().strip()

    db_user = db.query(User).filter(func.lower(User.email) == email).first()
    if not db_user:
        logger.warning("Login failed for %s: user not found", email)
        # Use constant-time comparison with dummy hash to prevent timing attacks
        verify_password(password, hash_password("dummy"))
        return None

    try:
        password_ok = verify_password(password, db_user.hashed_password)
    except Exception:
        logger.exception("Login failed for %s: stored password hash is invalid", email)
        return None

    if not password_ok:
        logger.warning("Login failed for %s: invalid password", email)
        return None

    logger.info("Login success for %s", email)
        
    return db_user


def create_token_response(user: User):
    """
    Create JWT token response for authenticated user.
    
    Includes:
    - access_token: JWT token for Bearer authentication
    - token_type: Always 'bearer'
    - role: User's role (patient, doctor, admin)
    - email: User's email address
    """
    access_token = create_access_token(data={"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "user_role": user.role,
        "role": user.role,
        "email": user.email,
    }


@router.post("/login", response_model=Token)
@limiter.limit(os.getenv("RATE_LIMIT_LOGIN", "10/minute"))
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login endpoint using OAuth2 form (application/x-www-form-urlencoded).

    **Parameters:**
    - username: Email address (sent as 'username' field in OAuth2 form)
    - password: Password (sent as 'password' field in OAuth2 form)

    **Returns:**
    - access_token: JWT token for API authentication (use in Authorization: Bearer header)
    - token_type: Always 'bearer'
    - role: User's role (patient, doctor, admin)
    - email: Confirmed email address
    
    **Errors:**
    - 401: Invalid email or password
    
    **Note:** This endpoint uses standard OAuth2 form encoding. For JSON body, use /login-json
    """
    if not form_data.username or not form_data.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required",
        )
    
    user = authenticate_user(form_data.username, form_data.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please check your credentials and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_token_response(user)


@router.post("/login-json", response_model=Token)
@limiter.limit(os.getenv("RATE_LIMIT_LOGIN", "10/minute"))
def login_json(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
    """
    Login endpoint accepting JSON body.

    **Parameters:** (JSON body)
    - email: User's email address
    - password: User's password

    **Returns:**
    - access_token: JWT token for API authentication (use in Authorization: Bearer header)
    - token_type: Always 'bearer'
    - role: User's role (patient, doctor, admin)
    - email: Confirmed email address
    
    **Errors:**
    - 401: Invalid email or password
    
    **Note:** This endpoint accepts JSON body. For form-encoded data, use /login
    """
    if not credentials.email or not credentials.password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Email and password are required",
        )
    
    user = authenticate_user(credentials.email, credentials.password, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password. Please check your credentials and try again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return create_token_response(user)


@router.get("/me", response_model=UserResponse)
def read_current_user(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get current authenticated user's profile.

    **Authentication:** Requires valid Bearer token

    **Returns:** Authenticated user profile
    - id: User's unique identifier
    - email: User's email address
    - role: User's role (patient, doctor, admin)
    - doctor_id: When role is doctor, the linked `doctors.id` for public profile URLs (null otherwise)

    **Errors:** 401 when token is invalid or missing
    """
    doctor_id = None
    if current_user.role == "doctor":
        doc = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
        if doc:
            doctor_id = doc.id
    return {
        "id": current_user.id,
        "email": current_user.email,
        "role": current_user.role,
        "doctor_id": doctor_id,
    }
