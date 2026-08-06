"""Independent PR #31 adversarial regressions.

Reproduces the audit exploits that previously returned FAIL:
1. Receptionist 100% invoice exemption (must be 403)
2. Duplicate X-Client-Request-Id must not create two invoices
"""

from __future__ import annotations

import uuid

import models
from core.auth_cookie_config import resolve_auth_cookie_samesite
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
            "tv": int(getattr(user, "token_version", 0) or 0),
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _seed_reception(db_session):
    suffix = uuid.uuid4().hex[:8]
    clinic = models.Clinic(name=f"PR31 Audit {suffix}", city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)
    with provisioning_channel("test_fixture"):
        receptionist = models.User(
            email=f"pr31.reception.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="receptionist",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        admin = models.User(
            email=f"pr31.admin.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="clinic_admin",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        db_session.add_all([receptionist, admin])
        db_session.commit()
        db_session.refresh(receptionist)
        db_session.refresh(admin)
    patient = models.Patient(
        first_name="Fatoumata",
        last_name="Camara",
        age=28,
        gender="f",
        clinic_id=clinic.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return clinic, receptionist, admin, patient


def _catalog_invoice_payload(patient_id: int, *, exemption_percent: float = 0, reason: str | None = None):
    body = {
        "patient_id": patient_id,
        "department": "Consultation externe",
        "items": [
            {
                "charge_type": "consultation",
                "description": "Consult",
                "quantity": 1,
                "unit_price_gnf": 1,
                "catalog_code": "emergency_consultation",
            }
        ],
        "exemption_percent": exemption_percent,
    }
    if reason is not None:
        body["exemption_reason"] = reason
    return body


def test_receptionist_cannot_self_approve_100_percent_exemption(client, db_session):
    _clinic, receptionist, _admin, patient = _seed_reception(db_session)
    response = client.post(
        "/clinical/reception/his/invoices",
        json=_catalog_invoice_payload(
            patient.id,
            exemption_percent=100,
            reason="self-approved write-off",
        ),
        headers=_auth(receptionist),
    )
    assert response.status_code == 403, response.text
    assert "billing.override" in response.text.lower() or "permission" in response.text.lower()


def test_clinic_admin_can_apply_exemption_with_reason(client, db_session):
    _clinic, _receptionist, admin, patient = _seed_reception(db_session)
    response = client.post(
        "/clinical/reception/his/invoices",
        json=_catalog_invoice_payload(
            patient.id,
            exemption_percent=100,
            reason="indigence medicale documentee",
        ),
        headers=_auth(admin),
    )
    assert response.status_code == 201, response.text
    payload = response.json()
    assert int(payload.get("total_amount_gnf") or 0) == 0
    assert int(payload.get("subtotal_amount_gnf") or 0) > 0


def test_client_request_id_is_idempotent_for_invoice_create(client, db_session):
    _clinic, receptionist, _admin, patient = _seed_reception(db_session)
    req_id = f"audit-idem-{uuid.uuid4().hex}"
    headers = {
        **_auth(receptionist),
        "X-Client-Request-Id": req_id,
    }
    body = _catalog_invoice_payload(patient.id)
    first = client.post("/clinical/reception/his/invoices", json=body, headers=headers)
    second = client.post("/clinical/reception/his/invoices", json=body, headers=headers)
    assert first.status_code == 201, first.text
    assert second.status_code == 201, second.text
    assert first.json()["id"] == second.json()["id"]
    assert second.headers.get("x-idempotent-replay") == "true"

    invoices = (
        db_session.query(models.Invoice)
        .filter(models.Invoice.patient_id == patient.id)
        .all()
    )
    assert len(invoices) == 1


def test_client_request_id_conflict_on_payload_mismatch(client, db_session):
    _clinic, receptionist, _admin, patient = _seed_reception(db_session)
    req_id = f"audit-conflict-{uuid.uuid4().hex}"
    headers = {
        **_auth(receptionist),
        "X-Client-Request-Id": req_id,
    }
    first = client.post(
        "/clinical/reception/his/invoices",
        json=_catalog_invoice_payload(patient.id),
        headers=headers,
    )
    assert first.status_code == 201, first.text
    second = client.post(
        "/clinical/reception/his/invoices",
        json={
            **_catalog_invoice_payload(patient.id),
            "department": "Hospitalisation",
        },
        headers=headers,
    )
    assert second.status_code == 409, second.text


def test_deployed_cookie_samesite_defaults_to_none(monkeypatch):
    monkeypatch.delenv("AUTH_COOKIE_SAMESITE", raising=False)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "production")
    monkeypatch.setenv("ENVIRONMENT", "production")
    assert resolve_auth_cookie_samesite() == "none"


def test_local_cookie_samesite_defaults_to_lax(monkeypatch):
    monkeypatch.delenv("AUTH_COOKIE_SAMESITE", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert resolve_auth_cookie_samesite() == "lax"
