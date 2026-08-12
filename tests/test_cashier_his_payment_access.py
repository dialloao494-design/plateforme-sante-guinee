"""Cashier must be able to read HIS invoices and record payments (BILLING_PAY_ROLES)."""

from __future__ import annotations

import uuid
from datetime import date

import models
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


def _seed(db_session):
    suffix = uuid.uuid4().hex[:8]
    clinic = models.Clinic(name=f"Cashier Pay {suffix}", city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"recv.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="receptionist",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        cashier = models.User(
            email=f"cash.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="cashier",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        doctor = models.User(
            email=f"doc.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="doctor",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        db_session.add_all([reception, cashier, doctor])
        db_session.commit()
        for u in (reception, cashier, doctor):
            db_session.refresh(u)
    patient = models.Patient(
        first_name="Awa",
        last_name="Diallo",
        age=28,
        gender="f",
        clinic_id=clinic.id,
        phone="620111222",
        patient_number=f"PAT-{clinic.id:03d}-000001",
        qr_token=f"QR-{suffix}",
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return clinic, reception, cashier, doctor, patient


def test_cashier_can_pay_his_invoice(client, db_session):
    clinic, reception, cashier, doctor, patient = _seed(db_session)
    inv = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Médecine",
            "billing_date": str(date.today()),
            "exemption_percent": 0,
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "Consultation spécialisée — Médecine",
                    "quantity": 1,
                    "catalog_code": "medicine",
                    "price_variant": "specialized",
                }
            ],
        },
        headers=_auth(reception),
    )
    assert inv.status_code == 201, inv.text
    invoice_id = inv.json()["id"]
    amount = inv.json().get("total_amount_gnf") or inv.json().get("amount_due_gnf") or 250000

    # Doctor still denied
    deny = client.post(
        f"/clinical/reception/his/invoices/{invoice_id}/payments",
        json={"amount_gnf": int(amount), "payment_method": "cash"},
        headers=_auth(doctor),
    )
    assert deny.status_code == 403, deny.text

    # Cashier can read + pay
    get_inv = client.get(
        f"/clinical/reception/his/invoices/{invoice_id}",
        headers=_auth(cashier),
    )
    assert get_inv.status_code == 200, get_inv.text

    pay = client.post(
        f"/clinical/reception/his/invoices/{invoice_id}/payments",
        json={"amount_gnf": int(amount), "payment_method": "cash", "reference": "CASH-E2E"},
        headers=_auth(cashier),
    )
    assert pay.status_code in (200, 201), pay.text
    assert pay.json().get("status") in ("paid", "partially_paid", "settled") or pay.json().get(
        "paid_amount_gnf", 0
    ) >= int(amount)
