from passlib.context import CryptContext
from jose import jwt
from datetime import datetime, timedelta
from fastapi import Depends, HTTPException, Request, status
from database import get_db
from sqlalchemy.orm import Session
from sqlalchemy import func
from models.user import User
import models
from core.roles import effective_role, roles_equivalent, user_has_any_role
from core.password_policy import validate_password  # noqa: F401 — re-export for schemas
from fastapi.security import OAuth2PasswordBearer
from dotenv import load_dotenv
import os
import uuid

load_dotenv()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

# ==============================
# PASSWORD CONFIG
# ==============================

_BCRYPT_ROUNDS = int(os.getenv("BCRYPT_ROUNDS", "12"))
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=_BCRYPT_ROUNDS,
)


def hash_password(password: str):
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


# ==============================
# JWT CONFIG
# ==============================

# Prefer SECRET_KEY; accept JWT_SECRET as alias (architecture / Railway templates).
SECRET_KEY = (os.getenv("SECRET_KEY") or os.getenv("JWT_SECRET") or "").strip()
ALGORITHM = (os.getenv("ALGORITHM") or "HS256").strip() or "HS256"
if ALGORITHM.upper() not in {"HS256"}:
    # Wave 0 keeps HS256 for backward compatibility; asymmetric is a later wave.
    ALGORITHM = "HS256"

# Architecture target: ≤15–30 minutes. Default 30; override via env without code change.
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

if not SECRET_KEY:
    raise ValueError("SECRET_KEY or JWT_SECRET environment variable is required")

# Paths allowed while must_change_password is set (suffix match).
_MUST_CHANGE_ALLOW_SUFFIXES = (
    "/auth/me",
    "/auth/change-password",
    "/auth/logout",
    "/auth/refresh",
    "/auth/mfa/setup",
    "/auth/mfa/confirm",
    "/auth/mfa/disable",
)


def create_access_token(data: dict, *, expires_minutes: int | None = None):
    to_encode = data.copy()
    minutes = ACCESS_TOKEN_EXPIRE_MINUTES if expires_minutes is None else expires_minutes
    now = datetime.utcnow()
    expire = now + timedelta(minutes=minutes)
    # Always issue a non-empty jti (reject attacker-supplied empty string).
    existing_jti = str(to_encode.get("jti") or "").strip()
    to_encode["jti"] = existing_jti or str(uuid.uuid4())
    if "iat" not in to_encode:
        to_encode["iat"] = now
    if "tv" not in to_encode and "token_version" in to_encode:
        to_encode["tv"] = to_encode.pop("token_version")
    to_encode["exp"] = expire
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


def _path_allowed_during_must_change(path: str) -> bool:
    normalized = (path or "").rstrip("/") or "/"
    for suffix in _MUST_CHANGE_ALLOW_SUFFIXES:
        if normalized.endswith(suffix.rstrip("/")) or normalized.endswith(suffix):
            return True
    return False


def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
        token_role = payload.get("user_role") or payload.get("role")
        email: str = payload.get("sub")
        jti = payload.get("jti")
        token_version = payload.get("tv", payload.get("token_version"))

        if user_id is None and email is None:
            raise credentials_exception
        # Deny missing/blank jti so denylist and logout cannot be bypassed.
        if not isinstance(jti, str) or not str(jti).strip():
            raise credentials_exception

    except HTTPException:
        raise
    except Exception:
        raise credentials_exception

    from services.auth_session_service import is_access_jti_denied

    if is_access_jti_denied(db, jti=jti):
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

    user_tv = int(getattr(user, "token_version", 0) or 0)
    if token_version is None:
        # Legacy tokens without tv: accept only when user has never rotated (tv==0).
        if user_tv != 0:
            raise credentials_exception
    elif int(token_version) != user_tv:
        raise credentials_exception

    if bool(getattr(user, "must_change_password", False)):
        path = request.url.path if request else ""
        if not _path_allowed_during_must_change(path):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Password change required before continuing",
                headers={"X-Password-Change-Required": "1"},
            )

    return user


def require_roles(required_roles: list[str]):
    def role_dependency(current_user: User = Depends(get_current_user)):
        if not user_has_any_role(current_user.role, required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Operation requires one of roles: {required_roles}",
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
        payload = decode_access_token(token)
        user_id = payload.get("user_id")
        email: str = payload.get("sub")
        token_role = payload.get("user_role") or payload.get("role")
        jti = payload.get("jti")
        token_version = payload.get("tv", payload.get("token_version"))

        if user_id is None and email is None:
            return None
        if not isinstance(jti, str) or not str(jti).strip():
            return None

    except Exception:
        return None

    from services.auth_session_service import is_access_jti_denied

    if is_access_jti_denied(db, jti=jti):
        return None

    user = None
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
    if user is None and email is not None:
        en = email.lower().strip()
        user = db.query(User).filter(func.lower(User.email) == en).first()
    if user is None:
        return None
    if hasattr(user, "is_active") and user.is_active is False:
        return None
    if token_role and not roles_equivalent(token_role, user.role):
        return None
    user_tv = int(getattr(user, "token_version", 0) or 0)
    if token_version is None:
        if user_tv != 0:
            return None
    elif int(token_version) != user_tv:
        return None
    return user
