from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, status
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.user import User
import models
from core.roles import effective_role, roles_equivalent, user_has_any_role
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import os
import re

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ==============================
# PASSWORD CONFIG
# ==============================

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def validate_password(password: str):
    """Validate password strength"""
    if len(password) < 8:
        raise ValueError("Password must be at least 8 characters long")
    if not re.search(r"[A-Z]", password):
        raise ValueError("Password must contain at least one uppercase letter")
    if not re.search(r"[0-9]", password):
        raise ValueError("Password must contain at least one digit")
    return True


def validate_role(role: str) -> str:
    """Validate that role is a known platform role (including admin for internal use)."""
    from core.roles import assert_known_role

    return assert_known_role(role)


# ==============================
# JWT CONFIG
# ==============================

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is required")


def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        token_role = payload.get("user_role") or payload.get("role")
        email: str = payload.get("sub")

        if user_id is None and email is None:
            raise credentials_exception

    except Exception:
        raise credentials_exception

    user = None
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()

    if user is None and email is not None:
        en = email.lower().strip()
        user = db.query(User).filter(func.lower(User.email) == en).first()

    if user is None:
        raise credentials_exception

    if hasattr(user, "is_active") and user.is_active is False:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    if token_role and not roles_equivalent(token_role, user.role):
        raise credentials_exception

    return user


def require_roles(required_roles: list[str]):
    def role_dependency(current_user: User = Depends(get_current_user)):
        if not user_has_any_role(current_user.role, required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied",
            )
        return current_user

    return role_dependency


def get_current_platform_owner(current_user: User = Depends(get_current_user)):
    if not user_has_any_role(current_user.role, ["platform_owner"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform owner privileges required",
        )
    return current_user


def get_current_platform_admin(current_user: User = Depends(get_current_user)):
    if not user_has_any_role(current_user.role, ["platform_owner", "platform_admin"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator privileges required",
        )
    return current_user


def get_current_clinic_admin(current_user: User = Depends(get_current_user)):
    if not user_has_any_role(
        current_user.role, ["clinic_admin", "admin", "platform_admin", "platform_owner"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Clinic administrator privileges required",
        )
    return current_user


def get_current_admin(current_user: User = Depends(get_current_user)):
    """Clinic or platform admin (not platform owner portal — use get_current_platform_owner)."""
    if not user_has_any_role(
        current_user.role, ["platform_owner", "platform_admin", "clinic_admin", "admin"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def get_current_doctor(current_user: User = Depends(get_current_user)):
    if not user_has_any_role(current_user.role, ["doctor"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor privileges required",
        )
    return current_user


def get_current_patient(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not user_has_any_role(current_user.role, ["patient"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient privileges required",
        )

    # Self-heal legacy accounts: create missing patient profile on first protected access.
    patient_profile = db.query(models.Patient).filter(
        models.Patient.user_id == current_user.id
    ).first()
    if not patient_profile:
        patient_profile = models.Patient(
            user_id=current_user.id,
            first_name="Patient",
            last_name=f"User{current_user.id}",
            age=0,
            gender="unknown",
        )
        db.add(patient_profile)
        db.commit()

    return current_user


def require_patient(current_user: User = Depends(get_current_user)):
    if not user_has_any_role(current_user.role, ["patient"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Patient privileges required",
        )
    return current_user


def require_doctor(current_user: User = Depends(get_current_user)):
    if not user_has_any_role(current_user.role, ["doctor"]):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Doctor privileges required",
        )
    return current_user


def require_admin(current_user: User = Depends(get_current_user)):
    if not user_has_any_role(
        current_user.role, ["platform_owner", "platform_admin", "clinic_admin", "admin"]
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required",
        )
    return current_user


def get_current_user_or_none(
    token: str | None = Depends(oauth2_scheme_optional),
    db: Session = Depends(get_db),
):
    """Optional authentication dependency. Returns None if no token is provided or valid."""
    if token is None:
        return None
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        email: str = payload.get("sub")

        if user_id is None and email is None:
            return None

    except Exception:
        return None

    user = None
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
    if user is None and email is not None:
        en = email.lower().strip()
        user = db.query(User).filter(func.lower(User.email) == en).first()
    return user
