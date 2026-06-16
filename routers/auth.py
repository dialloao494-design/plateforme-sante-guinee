import logging

import os

from fastapi import APIRouter, Depends, HTTPException, Request, status
from core.limiter import limiter, login_rate_limit, register_rate_limit
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
import models
from schemas.user import PublicRegistration, UserLogin, UserResponse, Token, ChangePasswordRequest
from security import (
    get_current_user,
    hash_password,
    verify_password,
    create_access_token,
)
from services.user_provisioning import (
    EmailAlreadyRegisteredError,
    PublicRegistrationRoleError,
    PrivilegedRoleAssignmentError,
    UserProvisioningError,
    register_public_user,
)
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)


@router.post("/register", response_model=UserResponse, status_code=201)
@limiter.limit(register_rate_limit())
def register(request: Request, user: PublicRegistration, db: Session = Depends(get_db)):
    """
    Public self-service registration (patient or doctor only).

    Administrator accounts cannot be created through this endpoint.
    Use ``POST /users/admins`` with an authenticated admin session, or ops bootstrap
    (``ENABLE_ADMIN_BOOTSTRAP``) for the first admin on a new environment.

    Raises:
    - 409: Email already registered
    - 422: Validation error (invalid email, password, role, or unknown fields)
    """
    try:
        provisioned = register_public_user(
            db,
            email=user.email,
            password=user.password,
            role=user.role,
        )
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except (PublicRegistrationRoleError, PrivilegedRoleAssignmentError) as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except UserProvisioningError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    new_user = provisioned.user
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        role=new_user.role,
        doctor_id=provisioned.doctor_id,
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
@limiter.limit(login_rate_limit())
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
@limiter.limit(login_rate_limit())
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


def build_user_response(db: Session, user: User) -> dict:
    """Enrich user profile with display name and clinic context."""
    doctor_id = None
    full_name = None
    clinic_id = user.clinic_id
    clinic_name = None

    if user.role == "doctor":
        doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if doc:
            doctor_id = doc.id
            full_name = doc.full_name
            if clinic_id is None:
                clinic_id = doc.clinic_id
    elif user.role == "patient":
        pat = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
        if pat and pat.first_name:
            full_name = f"{pat.first_name} {pat.last_name}".strip()
            if clinic_id is None:
                clinic_id = pat.clinic_id

    if not full_name:
        local = (user.email or "").split("@")[0]
        full_name = local.replace(".", " ").replace("_", " ").strip().title() or user.email

    if clinic_id:
        clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
        if clinic:
            clinic_name = clinic.name
    elif user.role == "platform_admin":
        clinic_name = "Plateforme nationale"

    return {
        "id": user.id,
        "email": user.email,
        "role": user.role,
        "doctor_id": doctor_id,
        "full_name": full_name,
        "clinic_id": clinic_id,
        "clinic_name": clinic_name,
    }


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
    return build_user_response(db, current_user)


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Change password for the authenticated user."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )
    current_user.hashed_password = hash_password(body.new_password)
    db.add(current_user)
    db.commit()
    logger.info("Password changed for user id=%s", current_user.id)
    return {"message": "Mot de passe mis à jour"}
