import logging

import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from core.limiter import limiter, login_rate_limit, register_rate_limit, forgot_password_rate_limit
from sqlalchemy import func
from sqlalchemy.orm import Session
from database import get_db
from models.user import User
import models
from schemas.user import (
    PublicRegistration,
    UserLogin,
    UserResponse,
    Token,
    RegisterResponse,
    ChangePasswordRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
    ResendVerificationRequest,
    RefreshTokenRequest,
    LogoutRequest,
    MfaSetupConfirmRequest,
    MfaVerifyLoginRequest,
    MfaDisableRequest,
    UserProfileUpdate,
    StaffActivationInspectRequest,
    StaffActivationCompleteRequest,
)
from security import (
    get_current_user,
    get_current_user_or_none,
    get_access_token_from_request,
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from core.roles import effective_role
from services.user_provisioning import (
    EmailAlreadyRegisteredError,
    PublicRegistrationRoleError,
    PrivilegedRoleAssignmentError,
    UserProvisioningError,
    register_public_user,
)
from services.password_reset_service import (
    create_reset_token,
    reset_password_with_token,
    send_reset_email,
)
from services.email_verification_service import verify_email_with_token, resend_verification
from services.email_service import email_config_status
from services.staff_activation_service import ActivationError, complete_activation, inspect_activation
from services.auth_session_service import (
    issue_refresh_token,
    rotate_refresh_token,
    revoke_refresh_token,
    revoke_all_user_refresh_tokens,
    denylist_access_jti,
    check_account_lockout,
    record_login_failure,
    record_login_success,
    bump_token_version,
    client_meta,
)
from services.mfa_service import (
    generate_mfa_secret,
    provisioning_uri,
    verify_totp,
    user_needs_mfa_challenge,
    mfa_required_for_user,
)
from core.auth_cookie_config import REFRESH_COOKIE_NAME
from services.auth_cookies import clear_auth_cookies, ensure_csrf_cookie, set_auth_cookies
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

router = APIRouter(prefix="/auth", tags=["Auth"])
logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


@router.post("/staff-activation/inspect")
@limiter.limit("20/minute")
def inspect_staff_activation(request: Request, body: StaffActivationInspectRequest, db: Session = Depends(get_db)):
    try:
        return inspect_activation(db, body.token)
    except ActivationError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/staff-activation/complete")
@limiter.limit("10/minute")
def activate_staff_account(request: Request, body: StaffActivationCompleteRequest, db: Session = Depends(get_db)):
    try:
        user = complete_activation(db, token=body.token, password=body.password)
    except (ActivationError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return {"activated": True, "email": user.email}


def _enforce_mfa_on_login(user: User, mfa_code: str | None) -> None:
    if user_needs_mfa_challenge(user):
        if not mfa_code or not verify_totp(user.mfa_secret, mfa_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="MFA code required",
                headers={"WWW-Authenticate": "Bearer", "X-MFA-Required": "1"},
            )
    elif mfa_required_for_user(user) and not bool(getattr(user, "mfa_enabled", False)):
        # Hard gate: privileged roles listed in MFA_REQUIRED_ROLES must enroll MFA.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="MFA enrollment required before login for this role",
            headers={"X-MFA-Enrollment-Required": "1"},
        )


@router.post("/register", response_model=RegisterResponse, status_code=201)
@limiter.limit(register_rate_limit())
def register(
    request: Request,
    response: Response,
    user: PublicRegistration,
    db: Session = Depends(get_db),
):
    """
    Public self-service registration (patient or doctor only).
    Returns a session token so the user can log in immediately after signup.
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
    db.refresh(new_user)

    if not verify_password(user.password, new_user.hashed_password):
        logger.error("Register integrity failure: password hash mismatch for user id=%s", new_user.id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erreur lors de la création du compte. Réessayez ou contactez le support.",
        )

    token_data = create_token_response(db, new_user, request=request, response=response)
    return RegisterResponse(
        id=new_user.id,
        email=new_user.email,
        role=new_user.role,
        doctor_id=provisioned.doctor_id,
        access_token=token_data["access_token"],
        token_type=token_data["token_type"],
        user_id=token_data["user_id"],
        user_role=token_data["user_role"],
        refresh_token=token_data.get("refresh_token"),
        must_change_password=token_data.get("must_change_password", False),
        expires_in=token_data.get("expires_in"),
        csrf_token=token_data.get("csrf_token"),
    )


def authenticate_user(email: str, password: str, db: Session, attempt_limit: int = 1000):
    """
    Authenticate user by email and password.

    Returns User object if credentials are valid, None otherwise.
    Applies account lockout and progressive soft-lock on failures.
    """
    del attempt_limit  # legacy kwarg retained for call-site compatibility
    email = email.lower().strip()

    db_user = db.query(User).filter(func.lower(User.email) == email).first()
    if not db_user:
        logger.warning("Login failed for %s: user not found", email)
        verify_password(password, hash_password("dummy"))
        return None

    try:
        check_account_lockout(db_user)
    except HTTPException:
        raise

    try:
        password_ok = verify_password(password, db_user.hashed_password)
    except Exception:
        logger.exception("Login failed for %s: stored password hash is invalid", email)
        record_login_failure(db, db_user)
        return None

    if not password_ok:
        logger.warning("Login failed for %s: invalid password", email)
        record_login_failure(db, db_user)
        return None

    if hasattr(db_user, "is_active") and db_user.is_active is False:
        logger.warning("Login failed for %s: account disabled", email)
        return None

    require_verify = os.getenv("REQUIRE_EMAIL_VERIFICATION", "").lower() in ("1", "true", "yes")
    if require_verify and not getattr(db_user, "email_verified_at", None):
        logger.warning("Login failed for %s: email not verified", email)
        return None

    record_login_success(db, db_user)
    logger.info("Login success for %s", email)
    return db_user


def _json_tokens_enabled() -> bool:
    """Return bearer tokens in login/refresh JSON for SPA clients.

    The production frontend (Vercel) and API (Railway) are cross-site. Safari/iOS
    Intelligent Tracking Prevention blocks third-party cookies, so cookie-only
    auth breaks clinic login and PDF printing. Always include tokens in JSON
    unless AUTH_JSON_TOKENS is explicitly set to false.
    """
    override = os.getenv("AUTH_JSON_TOKENS")
    if override is not None:
        return override.strip().lower() in {"1", "true", "yes", "on"}
    return True


def _create_access_token_for_user(user: User) -> tuple[str, str]:
    canonical_role = effective_role(user.role)
    token_version = int(getattr(user, "token_version", 0) or 0)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "user_role": canonical_role,
            "role": canonical_role,
            "session_version": int(getattr(user, "session_version", 0) or 0),
            "tv": token_version,
        }
    )
    return access_token, canonical_role


def _token_response_payload(
    *,
    user: User,
    access_token: str,
    refresh_token: str,
    canonical_role: str,
    csrf_token: str | None = None,
) -> dict:
    include_secret_tokens = _json_tokens_enabled()
    payload = {
        "access_token": access_token if include_secret_tokens else None,
        "refresh_token": refresh_token if include_secret_tokens else None,
        "token_type": "bearer",
        "user_id": user.id,
        "user_role": canonical_role,
        "role": canonical_role,
        "email": user.email,
        "must_change_password": bool(getattr(user, "must_change_password", False)),
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "csrf_token": csrf_token,
    }
    return payload


def create_token_response(
    db: Session,
    user: User,
    *,
    request: Request | None = None,
    response: Response | None = None,
):
    """Create access + refresh session and attach browser auth cookies when possible."""
    access_token, canonical_role = _create_access_token_for_user(user)
    ua, ip = client_meta(request) if request is not None else (None, None)
    refresh_raw, _ = issue_refresh_token(
        db, user=user, user_agent=ua, ip_address=ip
    )
    csrf_token = None
    if response is not None:
        csrf_token = set_auth_cookies(
            response,
            access_token=access_token,
            refresh_token=refresh_raw,
            access_max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            request=request,
        )
    return _token_response_payload(
        user=user,
        access_token=access_token,
        refresh_token=refresh_raw,
        canonical_role=canonical_role,
        csrf_token=csrf_token,
    )


@router.post("/login", response_model=Token)
@limiter.limit(login_rate_limit())
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
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
    _enforce_mfa_on_login(user, None)
    return create_token_response(db, user, request=request, response=response)


@router.post("/login-json", response_model=Token)
@limiter.limit(login_rate_limit())
def login_json(
    request: Request,
    response: Response,
    credentials: UserLogin,
    db: Session = Depends(get_db),
):
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
    _enforce_mfa_on_login(user, credentials.mfa_code)
    return create_token_response(db, user, request=request, response=response)


@router.post("/refresh", response_model=Token)
@limiter.limit(login_rate_limit())
def refresh_session(
    request: Request,
    response: Response,
    body: RefreshTokenRequest | None = None,
    db: Session = Depends(get_db),
):
    """Rotate refresh token and issue a new access token."""
    raw_refresh = (body.refresh_token if body else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    if not raw_refresh:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    ua, ip = client_meta(request)
    user, new_refresh, _ = rotate_refresh_token(
        db,
        raw_token=raw_refresh,
        user_agent=ua,
        ip_address=ip,
    )
    # Issue access only (reuse rotated refresh already created)
    access_token, canonical_role = _create_access_token_for_user(user)
    csrf_token = set_auth_cookies(
        response,
        access_token=access_token,
        refresh_token=new_refresh,
        access_max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        request=request,
    )
    return _token_response_payload(
        user=user,
        access_token=access_token,
        refresh_token=new_refresh,
        canonical_role=canonical_role,
        csrf_token=csrf_token,
    )


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    body: LogoutRequest | None = None,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_or_none),
):
    """
    Server-side logout: revoke refresh family and denylist current access jti.
    Accepts optional refresh_token in body/cookie; also works with Bearer access token only.
    """
    refresh = (body.refresh_token if body else None) or request.cookies.get(REFRESH_COOKIE_NAME)
    if refresh:
        revoke_refresh_token(db, raw_token=refresh)
    elif current_user is not None:
        revoke_all_user_refresh_tokens(db, user_id=current_user.id)

    if current_user is not None:
        current_user.session_version = int(getattr(current_user, "session_version", 0) or 0) + 1
        db.add(current_user)
        db.commit()

    access_token = get_access_token_from_request(request, token)
    if access_token:
        try:
            payload = decode_access_token(access_token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            expires_at = (
                datetime.utcfromtimestamp(exp)
                if isinstance(exp, (int, float))
                else datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            denylist_access_jti(
                db,
                jti=jti,
                user_id=current_user.id if current_user else None,
                expires_at=expires_at,
                reason="logout",
            )
        except Exception:
            logger.debug("Logout denylist skipped: invalid access token", exc_info=True)

    clear_auth_cookies(response, request=request)
    return {"message": "Logged out"}


def build_user_response(db: Session, user: User) -> dict:
    """Enrich user profile with display name and clinic context."""
    doctor_id = None
    first_name = (getattr(user, "first_name", None) or "").strip() or None
    last_name = (getattr(user, "last_name", None) or "").strip() or None
    full_name = " ".join(part for part in (first_name, last_name) if part) or None
    clinic_id = user.clinic_id
    clinic_name = None

    canonical_role = effective_role(user.role)

    if canonical_role == "doctor":
        doc = db.query(models.Doctor).filter(models.Doctor.user_id == user.id).first()
        if doc:
            doctor_id = doc.id
            if not full_name:
                first_name = doc.first_name
                last_name = doc.last_name
                full_name = doc.full_name
            if clinic_id is None:
                clinic_id = doc.clinic_id
    elif canonical_role == "patient":
        pat = db.query(models.Patient).filter(models.Patient.user_id == user.id).first()
        if pat and pat.first_name:
            if not full_name:
                first_name = pat.first_name
                last_name = pat.last_name
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
    elif canonical_role in ("platform_admin", "platform_owner"):
        clinic_name = "Plateforme nationale"
    else:
        staff_link = (
            db.query(models.ClinicStaff)
            .filter(models.ClinicStaff.user_id == user.id, models.ClinicStaff.is_active.is_(True))
            .order_by(models.ClinicStaff.id.desc())
            .first()
        )
        if staff_link:
            clinic_id = staff_link.clinic_id
            clinic = db.query(models.Clinic).filter(models.Clinic.id == clinic_id).first()
            if clinic:
                clinic_name = clinic.name

    return {
        "id": user.id,
        "email": user.email,
        "role": canonical_role,
        "doctor_id": doctor_id,
        "full_name": full_name,
        "first_name": first_name,
        "last_name": last_name,
        "clinic_id": clinic_id,
        "clinic_name": clinic_name,
        "email_verified": bool(getattr(user, "email_verified_at", None)),
        "must_change_password": bool(getattr(user, "must_change_password", False)),
        "mfa_enabled": bool(getattr(user, "mfa_enabled", False)),
    }


@router.get("/me", response_model=UserResponse)
def read_current_user(
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payload = build_user_response(db, current_user)
    payload["csrf_token"] = ensure_csrf_cookie(response, request)
    return payload


@router.patch("/me", response_model=UserResponse)
def update_current_user_profile(
    body: UserProfileUpdate,
    request: Request,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update the authenticated user's display identity only."""
    current_user.first_name = body.first_name
    current_user.last_name = body.last_name

    # Doctor names are operational data used by Reception assignment lists.
    if effective_role(current_user.role) == "doctor":
        doctor = db.query(models.Doctor).filter(models.Doctor.user_id == current_user.id).first()
        if doctor:
            doctor.first_name = body.first_name
            doctor.last_name = body.last_name
            db.add(doctor)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    payload = build_user_response(db, current_user)
    payload["csrf_token"] = ensure_csrf_cookie(response, request)
    return payload


@router.post("/change-password")
def change_password(
    request: Request,
    response: Response,
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    token: str | None = Depends(oauth2_scheme),
):
    """Change password for the authenticated user; revokes prior sessions."""
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Mot de passe actuel incorrect",
        )
    if verify_password(body.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Le nouveau mot de passe doit être différent de l'actuel",
        )

    current_user.hashed_password = hash_password(body.new_password)
    current_user.session_version = int(current_user.session_version or 0) + 1
    if hasattr(current_user, "must_change_password"):
        current_user.must_change_password = False
    bump_token_version(db, current_user)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    access_token = get_access_token_from_request(request, token)
    if access_token:
        try:
            payload = decode_access_token(access_token)
            jti = payload.get("jti")
            exp = payload.get("exp")
            expires_at = (
                datetime.utcfromtimestamp(exp)
                if isinstance(exp, (int, float))
                else datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            denylist_access_jti(
                db,
                jti=jti,
                user_id=current_user.id,
                expires_at=expires_at,
                reason="password_change",
            )
        except Exception:
            pass

    # Issue fresh session so the client can continue without re-login friction
    fresh = create_token_response(db, current_user, request=request, response=response)
    logger.info("Password changed for user id=%s", current_user.id)
    return {
        "message": "Mot de passe mis à jour",
        **fresh,
        "must_change_password": False,
    }


@router.post("/forgot-password")
@limiter.limit(forgot_password_rate_limit())
def forgot_password(
    request: Request,
    body: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    raw = create_reset_token(db, email=body.email)
    if raw:
        send_reset_email(body.email, raw)
    return {"message": "Si cet email est enregistré, un lien de réinitialisation a été envoyé."}


@router.post("/reset-password")
@limiter.limit(register_rate_limit())
def reset_password(
    request: Request,
    body: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    ok = reset_password_with_token(db, raw_token=body.token, new_password=body.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien invalide ou expiré. Demandez une nouvelle réinitialisation.",
        )
    return {"message": "Mot de passe réinitialisé. Vous pouvez vous connecter."}


@router.get("/email-status")
def email_delivery_status():
    return email_config_status()


@router.post("/verify-email")
@limiter.limit(register_rate_limit())
def verify_email(
    request: Request,
    body: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    ok = verify_email_with_token(db, raw_token=body.token)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Lien de vérification invalide ou expiré.",
        )
    return {"message": "Adresse email confirmée. Vous pouvez vous connecter."}


@router.post("/resend-verification")
@limiter.limit(forgot_password_rate_limit())
def resend_verification_email(
    request: Request,
    body: ResendVerificationRequest,
    db: Session = Depends(get_db),
):
    resend_verification(db, email=body.email)
    return {"message": "Si cet email est enregistré et non vérifié, un nouveau lien a été envoyé."}


@router.post("/mfa/setup")
def mfa_setup(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Begin TOTP enrollment; returns secret + otpauth URI (confirm to enable)."""
    secret = generate_mfa_secret()
    current_user.mfa_secret = secret
    current_user.mfa_enabled = False
    db.add(current_user)
    db.commit()
    return {
        "secret": secret,
        "otpauth_uri": provisioning_uri(email=current_user.email, secret=secret),
        "enabled": False,
    }


@router.post("/mfa/confirm")
def mfa_confirm(
    body: MfaSetupConfirmRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA setup not started")
    if not verify_totp(current_user.mfa_secret, body.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    current_user.mfa_enabled = True
    db.add(current_user)
    db.commit()
    return {"mfa_enabled": True}


@router.post("/mfa/disable")
def mfa_disable(
    body: MfaDisableRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Mot de passe incorrect")
    if current_user.mfa_enabled and not verify_totp(current_user.mfa_secret or "", body.code):
        raise HTTPException(status_code=400, detail="Invalid MFA code")
    current_user.mfa_enabled = False
    current_user.mfa_secret = None
    db.add(current_user)
    db.commit()
    return {"mfa_enabled": False}
