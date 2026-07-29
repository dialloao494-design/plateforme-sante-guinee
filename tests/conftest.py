"""Shared pytest fixtures — isolated in-memory SQLite (single engine with the app)."""

from __future__ import annotations

import os

# MUST be set before database/main are imported.
# Force test-safe settings even when the shell inherits clinic-node env.
os.environ["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "test-secret-key-for-pytest-only-32chars-min"
)
if len(os.environ.get("SECRET_KEY", "")) < 32:
    os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only-32chars-min"
os.environ["ENVIRONMENT"] = "development"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["ALLOWED_HOSTS"] = "testserver,localhost,127.0.0.1,*"
os.environ.pop("ENABLE_ADMIN_BOOTSTRAP", None)
os.environ["ENABLE_PILOT_SEED"] = "false"
os.environ["ENABLE_STARTUP_TEST_USER"] = "false"
os.environ["RATE_LIMIT_PLATFORM_SETUP"] = "10000/minute"
os.environ["RATE_LIMIT_DEFAULT"] = "10000/minute"
os.environ.pop("TRUSTED_PROXY_HOSTS", None)
os.environ.pop("REMINDER_RESPOND_TOKEN", None)
# Wave 2 — virus scan off by default in tests unless a test enables stub mode.
os.environ.setdefault("ATTACHMENT_VIRUS_SCAN", "off")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# Single shared in-memory connection (avoids "no such table" with :memory: + TestClient).
import database

database.engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
database.SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=database.engine,
)

from database import Base, SessionLocal, engine, get_db
import models  # noqa: F401 — registers User ORM hooks
import models.patient  # noqa: F401
import models.doctor  # noqa: F401
import models.rendezvous  # noqa: F401
import models.payment  # noqa: F401
import models.availability  # noqa: F401
import models.message  # noqa: F401
import models.attachment_access_log  # noqa: F401
import models.clinical_note  # noqa: F401
import models.consultation_summary  # noqa: F401
import models.patient_document  # noqa: F401
import models.clinical_audit_log  # noqa: F401
import models.clinic  # noqa: F401
import models.clinical_consultation  # noqa: F401
import models.lab_order  # noqa: F401
import models.lab_result  # noqa: F401
import models.prescription  # noqa: F401
import models.pharmacy_order  # noqa: F401
import models.clinic_charge  # noqa: F401
import models.medical_history  # noqa: F401
import models.hospitalization  # noqa: F401
import models.clinical_visit  # noqa: F401
import models.invoice  # noqa: F401
import models.discharge  # noqa: F401
import models.imaging  # noqa: F401
import models.appointment_reminder  # noqa: F401
import models.pharmacy_inventory  # noqa: F401
import models.nutrition  # noqa: F401
import models.immunization  # noqa: F401
import models.password_reset_token  # noqa: F401
import models.email_verification_token  # noqa: F401
import models.nursing_care  # noqa: F401
import models.nurse_assessment  # noqa: F401
import models.clinic_charge_payment  # noqa: F401
import models.visit_workflow  # noqa: F401

from main import app
from security import hash_password
from models.user import User

Base.metadata.create_all(bind=engine)


@pytest.fixture()
def db_session() -> Session:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture()
def client(db_session: Session):
    def _override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def admin_user(db_session: Session) -> User:
    from core.provisioning_context import provisioning_channel

    email = "admin@clinic.test"
    existing = db_session.query(User).filter(User.email == email).first()
    if existing:
        return existing

    with provisioning_channel("test_fixture"):
        user = User(
            email=email,
            hashed_password=hash_password("AdminPass1"),
            role="platform_owner",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
    return user


@pytest.fixture()
def admin_headers(client: TestClient, admin_user: User) -> dict[str, str]:
    response = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass1"},
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
