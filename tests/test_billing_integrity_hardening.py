"""Billing integrity: catalog-authoritative prices, DSR idempotency, patient link."""

from __future__ import annotations

import uuid

import models
from core.provisioning_context import provisioning_channel
from data.aasma_billing_catalog import resolve_billing_catalog_item
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


def _seed(db_session):
    suffix = uuid.uuid4().hex[:8]
    clinic = models.Clinic(name=f"Billing Integrity {suffix}", city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)
    with provisioning_channel("test_fixture"):
        admin = models.User(
            email=f"billing.admin.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="clinic_admin",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        patient_user = models.User(
            email=f"billing.patient.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="patient",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        other_clinic = models.Clinic(name=f"Other {suffix}", city="Kindia", is_active=True)
        db_session.add_all([admin, patient_user, other_clinic])
        db_session.commit()
        db_session.refresh(admin)
        db_session.refresh(patient_user)
        db_session.refresh(other_clinic)
        foreign_user = models.User(
            email=f"foreign.patient.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="patient",
            clinic_id=other_clinic.id,
            is_active=True,
            token_version=0,
        )
        doctor_user = models.User(
            email=f"billing.doctor.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="doctor",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        db_session.add_all([foreign_user, doctor_user])
        db_session.commit()
        db_session.refresh(foreign_user)
        db_session.refresh(doctor_user)
    patient = models.Patient(
        first_name="Aissatou",
        last_name="Bah",
        age=30,
        gender="f",
        clinic_id=clinic.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return clinic, admin, patient, patient_user, foreign_user, doctor_user


def test_resolve_billing_catalog_item_surgical():
    row = resolve_billing_catalog_item("suture_simple")
    assert row is not None
    assert row["price_gnf"] == 150_000
    assert row["label"] == "Suture simple"


def test_service_request_ignores_tampered_catalog_price(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    create = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "surgery",
            "service_name": "FAKE NAME",
            "catalog_code": "suture_simple",
            "charge_type": "procedure",
            "unit_price_gnf": 1,  # tampered
            "status": "pending",
        },
        headers=_auth(admin),
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["service_name"] == "Suture simple"
    assert body["unit_price_gnf"] == 150_000
    assert body["charge_type"] == "procedure"


def test_service_request_unknown_catalog_code_rejected(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "surgery",
            "service_name": "X",
            "catalog_code": "does_not_exist_xyz",
            "unit_price_gnf": 10,
        },
        headers=_auth(admin),
    )
    assert r.status_code == 400, r.text


def test_dsr_cannot_be_billed_twice(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    headers = _auth(admin)
    create = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "surgery",
            "service_name": "Suture simple",
            "catalog_code": "suture_simple",
            "unit_price_gnf": 999999,
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    dsr = create.json()["request_number"]

    inv1 = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Chirurgie",
            "items": [
                {
                    "charge_type": "procedure",
                    "description": "ignored",
                    "quantity": 1,
                    "unit_price_gnf": 1,
                    "source_type": "service_request",
                    "source_ref": dsr,
                }
            ],
        },
        headers=headers,
    )
    assert inv1.status_code == 201, inv1.text
    assert inv1.json()["total_amount_gnf"] == 150_000
    item = inv1.json()["items"][0]
    assert "DSR-" in item["description"]
    assert item["unit_price_gnf"] == 150_000

    inv2 = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Chirurgie",
            "items": [
                {
                    "charge_type": "procedure",
                    "description": "dup",
                    "quantity": 1,
                    "unit_price_gnf": 1,
                    "source_type": "service_request",
                    "source_ref": dsr,
                }
            ],
        },
        headers=headers,
    )
    assert inv2.status_code == 409, inv2.text


def test_cancelled_dsr_cannot_be_billed(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    headers = _auth(admin)
    create = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "surgery",
            "service_name": "Suture simple",
            "catalog_code": "suture_simple",
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    req_id = create.json()["id"]
    dsr = create.json()["request_number"]
    cancel = client.patch(
        f"/clinical/reception/his/service-requests/{req_id}",
        json={"status": "cancelled"},
        headers=headers,
    )
    assert cancel.status_code == 200, cancel.text

    inv = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Chirurgie",
            "items": [
                {
                    "charge_type": "procedure",
                    "description": "x",
                    "quantity": 1,
                    "unit_price_gnf": 1,
                    "source_type": "service_request",
                    "source_ref": dsr,
                }
            ],
        },
        headers=headers,
    )
    assert inv.status_code == 400, inv.text


def test_exemption_requires_reason(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Consultation externe",
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "Consult",
                    "quantity": 1,
                    "unit_price_gnf": 10000,
                }
            ],
            "exemption_percent": 10,
        },
        headers=_auth(admin),
    )
    assert r.status_code == 422, r.text


def test_patient_create_rejects_non_patient_role(client, db_session):
    clinic, admin, _patient, _pu, _fu, doctor_user = _seed(db_session)
    r = client.post(
        "/patients/",
        json={
            "user_id": doctor_user.id,
            "first_name": "Bad",
            "last_name": "Link",
            "age": 20,
            "gender": "m",
        },
        headers=_auth(admin),
    )
    assert r.status_code == 400, r.text
    assert "patient role" in r.text.lower() or "patient" in r.text.lower()


def test_patient_create_rejects_cross_clinic_user(client, db_session):
    _clinic, admin, _patient, _pu, foreign_user, _doc = _seed(db_session)
    r = client.post(
        "/patients/",
        json={
            "user_id": foreign_user.id,
            "first_name": "Cross",
            "last_name": "Clinic",
            "age": 22,
            "gender": "f",
        },
        headers=_auth(admin),
    )
    assert r.status_code == 400, r.text


def test_patient_create_rejects_duplicate_link(client, db_session):
    clinic, admin, _patient, patient_user, *_ = _seed(db_session)
    headers = _auth(admin)
    first = client.post(
        "/patients/",
        json={
            "user_id": patient_user.id,
            "first_name": "One",
            "last_name": "Link",
            "age": 25,
            "gender": "f",
        },
        headers=headers,
    )
    assert first.status_code == 200, first.text
    second = client.post(
        "/patients/",
        json={
            "user_id": patient_user.id,
            "first_name": "Two",
            "last_name": "Link",
            "age": 26,
            "gender": "f",
        },
        headers=headers,
    )
    assert second.status_code == 409, second.text
