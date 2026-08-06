"""One-time Platform Owner setup — public only while no owner exists."""

from __future__ import annotations

import logging
import os

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from routers.auth import create_token_response
from schemas.user import PlatformOwnerSetupRequest, Token
from security import validate_password
from services.platform_setup_guard import enforce_setup_rate_limit
from services.user_provisioning import (
    EmailAlreadyRegisteredError,
    PlatformOwnerSetupClosedError,
    UserProvisioningError,
    platform_owner_exists,
    setup_first_platform_owner,
)

router = APIRouter(tags=["Platform Owner Setup"])
logger = logging.getLogger(__name__)


class PlatformSetupStatusResponse(BaseModel):
    setup_required: bool
    public_setup_enabled: bool


def _public_setup_enabled() -> bool:
    environment = (os.getenv("ENVIRONMENT") or "development").lower().strip()
    if environment not in {"production", "staging"}:
        return True
    return (os.getenv("ALLOW_PUBLIC_PLATFORM_OWNER_SETUP") or "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _reject_disposable_setup_email(email: str) -> None:
    """Block obvious demo/test emails in production setup."""
    if (os.getenv("ENVIRONMENT") or "development").lower() != "production":
        return
    local = email.split("@")[0].lower()
    if email.endswith("@sante-gn.test") or "demo" in local or local.startswith("test"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Use a permanent production email address for the platform owner account.",
        )


@router.get("/platform/setup/status", response_model=PlatformSetupStatusResponse)
def platform_setup_status(db: Session = Depends(get_db)):
    """Returns whether the first-time owner setup wizard should be shown."""
    # Clinic Node is local-first: never redirect staff to cloud platform-owner wizard.
    env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    if env in {"clinic-node", "clinic_node"}:
        return PlatformSetupStatusResponse(
            setup_required=False,
            public_setup_enabled=False,
        )
    enabled = _public_setup_enabled()
    return PlatformSetupStatusResponse(
        setup_required=enabled and not platform_owner_exists(db),
        public_setup_enabled=enabled,
    )


@router.post("/platform/setup", response_model=Token, status_code=status.HTTP_201_CREATED)
def complete_platform_owner_setup(
    registration: PlatformOwnerSetupRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    _: None = Depends(enforce_setup_rate_limit),
):
    """
    Create the first Platform Owner account (one-time only).

    Disabled permanently once a platform_owner user exists.
    Disabled entirely on Clinic Node appliances.
    """
    env = (os.getenv("ENVIRONMENT") or "").strip().lower()
    if env in {"clinic-node", "clinic_node"}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform owner setup is not available on Clinic Node. Use the local clinic admin account.",
        )
    if not _public_setup_enabled():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Public platform owner setup is disabled.",
        )
    if platform_owner_exists(db):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform owner setup is disabled. Sign in with your owner account.",
        )

    _reject_disposable_setup_email(registration.email)

    try:
        validate_password(registration.password)
        provisioned = setup_first_platform_owner(
            db,
            email=registration.email,
            password=registration.password,
        )
    except PlatformOwnerSetupClosedError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except EmailAlreadyRegisteredError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except UserProvisioningError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc

    owner = provisioned.user
    logger.info("Platform owner created via setup page id=%s email=%s", owner.id, owner.email)
    return create_token_response(db, owner, request=request, response=response)
