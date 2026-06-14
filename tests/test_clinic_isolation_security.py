"""Cross-clinic data isolation security tests."""

from __future__ import annotations

import uuid

import models
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def _seed_clinic(client, db_session, admin_user, label: str) -> tuple[int, models.User]:
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"{label} Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    assert r.status_code == 201, r.text
    clinic_id = r.json()["id"]
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"{label}.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add(reception)
        db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
        db_session.commit()
        db_session.refresh(reception)
    return clinic_id, reception


def test_patient_search_is_scoped_to_clinic(client, db_session, admin_user):
    clinic_a_id, reception_a = _seed_clinic(client, db_session, admin_user, "isoA")
    clinic_b_id, reception_b = _seed_clinic(client, db_session, admin_user, "isoB")

    r = client.post(
        "/clinical/reception/patients",
        json={
            "first_name": "UniqueAlpha",
            "last_name": "IsolationTest",
            "age": 40,
            "gender": "F",
            "phone": "+224622111001",
        },
        headers=_auth(reception_a),
    )
    assert r.status_code == 201, r.text
    patient_a_id = r.json()["id"]

    r = client.get(
        "/clinical/reception/patients",
        params={"q": "IsolationTest"},
        headers=_auth(reception_b),
    )
    assert r.status_code == 200
    ids_b = {row["id"] for row in r.json()}
    assert patient_a_id not in ids_b

    r = client.get(
        "/clinical/reception/patients",
        params={"q": "IsolationTest"},
        headers=_auth(reception_a),
    )
    assert r.status_code == 200
    ids_a = {row["id"] for row in r.json()}
    assert patient_a_id in ids_a
    assert clinic_a_id != clinic_b_id


def test_invoice_access_is_scoped_to_clinic(client, db_session, admin_user):
    clinic_a_id, reception_a = _seed_clinic(client, db_session, admin_user, "billA")
    clinic_b_id, _reception_b = _seed_clinic(client, db_session, admin_user, "billB")

    r = client.post(
        "/clinical/reception/patients",
        json={
            "first_name": "Billing",
            "last_name": "ScopedPatient",
            "age": 35,
            "gender": "M",
            "phone": "+224622111002",
        },
        headers=_auth(reception_a),
    )
    patient_id = r.json()["id"]

    with provisioning_channel("test_fixture"):
        cashier_a = models.User(
            email=f"cashier.a.{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="cashier",
            clinic_id=clinic_a_id,
        )
        cashier_b = models.User(
            email=f"cashier.b.{uuid.uuid4().hex[:6]}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="cashier",
            clinic_id=clinic_b_id,
        )
        db_session.add_all([cashier_a, cashier_b])
        db_session.commit()
        db_session.refresh(cashier_a)
        db_session.refresh(cashier_b)

    invoice = models.Invoice(
        clinic_id=clinic_a_id,
        patient_id=patient_id,
        invoice_number=f"INV-ISO-{uuid.uuid4().hex[:8]}",
        status="issued",
        total_amount_gnf=50_000,
        paid_amount_gnf=0,
    )
    db_session.add(invoice)
    db_session.commit()
    db_session.refresh(invoice)

    r = client.get(
        f"/clinical/billing/unified/invoices/{invoice.id}",
        headers=_auth(cashier_b),
    )
    assert r.status_code == 404


def test_patient_user_id_unique(db_session):
    with provisioning_channel("test_fixture"):
        user = models.User(
            email=f"dup.patient.{uuid.uuid4().hex[:8]}@test.com",
            hashed_password=hash_password("Secret12"),
            role="patient",
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    db_session.add(
        models.Patient(
            user_id=user.id,
            first_name="First",
            last_name="Profile",
            age=20,
            gender="F",
        )
    )
    db_session.commit()

    db_session.add(
        models.Patient(
            user_id=user.id,
            first_name="Second",
            last_name="Profile",
            age=21,
            gender="F",
        )
    )
    import pytest
    from sqlalchemy.exc import IntegrityError

    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
