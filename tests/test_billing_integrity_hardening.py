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
                    "catalog_code": "emergency_consultation",
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
    # Ownership policy returns 400 (legacy) or 403 with clinic mismatch detail.
    assert r.status_code in (400, 403), r.text
    assert "clinic" in r.text.lower() or "permission" in r.text.lower()


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


def test_free_text_service_request_requires_privilege(client, db_session):
    clinic, admin, patient, *_ = _seed(db_session)
    with provisioning_channel("test_fixture"):
        receptionist = models.User(
            email=f"billing.reception.{uuid.uuid4().hex[:8]}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="receptionist",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        db_session.add(receptionist)
        db_session.commit()
        db_session.refresh(receptionist)

    # Priced free-text without privilege → 403
    denied = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "other",
            "service_name": "Custom dressing",
            "unit_price_gnf": 25000,
            "price_override_reason": "Patient agreement",
        },
        headers=_auth(receptionist),
    )
    assert denied.status_code == 403, denied.text

    # Priced free-text missing reason → 400 even for admin
    missing_reason = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "other",
            "service_name": "Custom dressing",
            "unit_price_gnf": 25000,
        },
        headers=_auth(admin),
    )
    assert missing_reason.status_code == 400, missing_reason.text

    allowed = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "other",
            "service_name": "Custom dressing",
            "unit_price_gnf": 25000,
            "price_override_reason": "Patient agreement",
        },
        headers=_auth(admin),
    )
    assert allowed.status_code == 201, allowed.text
    assert allowed.json()["unit_price_gnf"] == 25000

    # Clinical (unpriced) free-text DSR remains allowed for reception workflow
    clinical = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "laboratory",
            "service_name": "NFS",
            "department": "Laboratoire",
        },
        headers=_auth(receptionist),
    )
    assert clinical.status_code == 201, clinical.text
    assert clinical.json()["unit_price_gnf"] is None


def test_catalog_override_requires_privilege_and_audits(client, db_session):
    clinic, admin, patient, *_ = _seed(db_session)
    with provisioning_channel("test_fixture"):
        receptionist = models.User(
            email=f"billing.reception2.{uuid.uuid4().hex[:8]}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="receptionist",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        db_session.add(receptionist)
        db_session.commit()
        db_session.refresh(receptionist)

    denied = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "surgery",
            "service_name": "Suture simple",
            "catalog_code": "suture_simple",
            "unit_price_gnf": 100_000,
            "price_override_reason": "Staff discount",
        },
        headers=_auth(receptionist),
    )
    assert denied.status_code == 403, denied.text

    ok = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "surgery",
            "service_name": "Suture simple",
            "catalog_code": "suture_simple",
            "unit_price_gnf": 100_000,
            "price_override_reason": "Staff discount",
        },
        headers=_auth(admin),
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["unit_price_gnf"] == 100_000
    assert "Staff discount" in (ok.json().get("notes") or "")


def test_invoice_line_without_catalog_rejected_for_receptionist(client, db_session):
    clinic, admin, patient, *_ = _seed(db_session)
    with provisioning_channel("test_fixture"):
        receptionist = models.User(
            email=f"billing.reception3.{uuid.uuid4().hex[:8]}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="receptionist",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        db_session.add(receptionist)
        db_session.commit()
        db_session.refresh(receptionist)

    r = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Consultation externe",
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "Consult ad-hoc",
                    "quantity": 1,
                    "unit_price_gnf": 10000,
                    "price_override_reason": "Walk-in",
                }
            ],
        },
        headers=_auth(receptionist),
    )
    assert r.status_code == 403, r.text


def test_invoice_catalog_tamper_ignored(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
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
                    "catalog_code": "suture_simple",
                }
            ],
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    assert r.json()["total_amount_gnf"] == 150_000


def test_legacy_total_amount_invoice_rejected(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Consultation externe",
            "description": "Legacy line",
            "total_amount_gnf": 50000,
        },
        headers=_auth(admin),
    )
    assert r.status_code == 422, r.text


def test_lab_catalog_code_resolves(client, db_session):
    row = resolve_billing_catalog_item("HEM_nfs_hemogramme_complet")
    assert row is not None
    assert row["price_gnf"] == 120_000
    assert row["charge_type"] == "lab"

    _clinic, admin, patient, *_ = _seed(db_session)
    create = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "laboratory",
            "service_name": "NFS",
            "catalog_code": "HEM_nfs_hemogramme_complet",
            "unit_price_gnf": 1,
        },
        headers=_auth(admin),
    )
    assert create.status_code == 201, create.text
    assert create.json()["unit_price_gnf"] == 120_000


def test_linkable_patient_accounts_search(client, db_session):
    clinic, admin, _patient, patient_user, foreign_user, _doctor = _seed(db_session)
    headers = _auth(admin)

    # Unlinked patient in clinic — searchable by email fragment
    email_q = patient_user.email.split("@")[0][:6]
    found = client.get(
        "/patients/linkable-accounts",
        params={"q": email_q},
        headers=headers,
    )
    assert found.status_code == 200, found.text
    ids = {row["id"] for row in found.json()}
    assert patient_user.id in ids
    assert foreign_user.id not in ids

    # After linking, account disappears from selector
    create = client.post(
        "/patients/",
        json={
            "user_id": patient_user.id,
            "first_name": "Linked",
            "last_name": "Now",
            "age": 28,
            "gender": "f",
        },
        headers=headers,
    )
    assert create.status_code == 200, create.text
    after = client.get(
        "/patients/linkable-accounts",
        params={"q": email_q},
        headers=headers,
    )
    assert after.status_code == 200, after.text
    assert patient_user.id not in {row["id"] for row in after.json()}
