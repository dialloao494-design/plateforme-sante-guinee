"""Pharmacy inventory backend."""

from __future__ import annotations

import uuid

import models
from security import create_access_token, hash_password
from core.provisioning_context import provisioning_channel


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def test_pharmacy_inventory_list_and_adjust(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Pharm Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        pharm = models.User(
            email=f"pharm.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="pharmacist",
            clinic_id=clinic_id,
        )
        db_session.add(pharm)
        db_session.commit()
        db_session.refresh(pharm)

    r = client.get("/clinical/pharmacy/inventory", headers=_auth(pharm))
    assert r.status_code == 200
    assert len(r.json()) >= 1

    item_id = r.json()[0]["id"]
    qty_before = r.json()[0]["quantity"]
    r = client.patch(
        f"/clinical/pharmacy/inventory/{item_id}",
        json={"delta": -5},
        headers=_auth(pharm),
    )
    assert r.status_code == 200
    assert r.json()["quantity"] == qty_before - 5


def test_pharmacy_stock_order_receipt_updates_inventory_and_is_tenant_scoped(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    response = client.post(
        "/clinical/clinics",
        json={"name": f"Stock Order Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = response.json()["id"]
    with provisioning_channel("test_fixture"):
        pharmacist = models.User(
            email=f"stock.{suffix}@test.com",
            hashed_password=hash_password("StaffPass12!"),
            role="pharmacist",
            clinic_id=clinic_id,
        )
        db_session.add(pharmacist)
        db_session.commit()
        db_session.refresh(pharmacist)

    inventory = client.get("/clinical/pharmacy/inventory", headers=_auth(pharmacist)).json()
    item = inventory[0]
    created = client.post(
        "/clinical/pharmacy/stock-orders",
        json={
            "inventory_item_id": item["id"],
            "medication_name": item["medication_name"],
            "quantity": 25,
            "supplier": "Grossiste Conakry",
        },
        headers=_auth(pharmacist),
    )
    assert created.status_code == 201, created.text
    order = created.json()
    assert order["order_number"].startswith(f"CMD-{clinic_id:03d}-")
    assert order["status"] == "ordered"

    received = client.post(
        f"/clinical/pharmacy/stock-orders/{order['id']}/receive",
        headers=_auth(pharmacist),
    )
    assert received.status_code == 200, received.text
    assert received.json()["status"] == "received"
    updated = client.get("/clinical/pharmacy/inventory", headers=_auth(pharmacist)).json()
    updated_item = next(row for row in updated if row["id"] == item["id"])
    assert updated_item["quantity"] == item["quantity"] + 25

    duplicate = client.post(
        f"/clinical/pharmacy/stock-orders/{order['id']}/receive",
        headers=_auth(pharmacist),
    )
    assert duplicate.status_code == 400


def test_pharmacy_refund_is_guarded_audited_and_restores_stock(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    clinic_id = client.post(
        "/clinical/clinics",
        json={"name": f"Refund Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    ).json()["id"]
    with provisioning_channel("test_fixture"):
        pharmacist = models.User(email=f"refund.pharm.{suffix}@test.com", hashed_password=hash_password("StaffPass12!"), role="pharmacist", clinic_id=clinic_id)
        doctor_user = models.User(email=f"refund.doctor.{suffix}@test.com", hashed_password=hash_password("StaffPass12!"), role="doctor", clinic_id=clinic_id)
        db_session.add_all([pharmacist, doctor_user])
        db_session.flush()
        db_session.add(models.Doctor(user_id=doctor_user.id, first_name="Aminata", last_name="Test", specialty="Médecine", city="Conakry", phone="620000001", clinic_id=clinic_id))
        patient = models.Patient(clinic_id=clinic_id, first_name="Mariam", last_name="Camara", age=32, gender="female", patient_number=f"PAT-{suffix}")
        db_session.add(patient)
        db_session.commit()
        db_session.refresh(pharmacist)
        db_session.refresh(patient)

    inventory = client.get("/clinical/pharmacy/inventory", headers=_auth(pharmacist)).json()
    item = next(row for row in inventory if row["quantity"] >= 2)
    request = client.post(
        "/clinical/pharmacy/service-requests",
        json={"patient_id": patient.id, "items": [{"product_name": item["medication_name"], "quantity": 2, "unit_price_gnf": 10000, "inventory_item_id": item["id"]}]},
        headers=_auth(pharmacist),
    )
    assert request.status_code == 201, request.text
    charge_id = request.json()["charge_id"]
    payment = client.post(
        f"/clinical/pharmacy/charges/{charge_id}/payments",
        json={"payment_method": "cash", "amount_gnf": 20000},
        headers=_auth(pharmacist),
    )
    assert payment.status_code == 200, payment.text
    after_sale = next(row for row in client.get("/clinical/pharmacy/inventory", headers=_auth(pharmacist)).json() if row["id"] == item["id"])
    assert after_sale["quantity"] == item["quantity"] - 2

    eligible = client.get("/clinical/pharmacy/refunds/eligible", headers=_auth(pharmacist))
    assert eligible.status_code == 200
    assert eligible.json()[0]["charge_id"] == charge_id
    refunded = client.post(
        "/clinical/pharmacy/refunds",
        json={"charge_id": charge_id, "items": [{"inventory_item_id": item["id"], "product_name": item["medication_name"], "quantity": 1, "return_to_stock": True}], "refund_method": "cash", "reason": "returned", "reason_notes": "Produit scellé retourné", "recipient_name": "Mariam Camara", "recipient_phone": "620000002"},
        headers=_auth(pharmacist),
    )
    assert refunded.status_code == 201, refunded.text
    assert refunded.json()["amount_gnf"] == 10000
    assert refunded.json()["refund_number"].startswith(f"RPH-{clinic_id:03d}-")
    restored = next(row for row in client.get("/clinical/pharmacy/inventory", headers=_auth(pharmacist)).json() if row["id"] == item["id"])
    assert restored["quantity"] == item["quantity"] - 1
    receipt = client.get(f"/clinical/pharmacy/refunds/{refunded.json()['id']}/receipt", headers=_auth(pharmacist))
    assert receipt.status_code == 200
    assert receipt.headers["content-type"].startswith("application/pdf")

    over_refund = client.post(
        "/clinical/pharmacy/refunds",
        json={"charge_id": charge_id, "items": [{"inventory_item_id": item["id"], "product_name": item["medication_name"], "quantity": 2, "return_to_stock": False}], "refund_method": "cash", "reason": "returned", "reason_notes": "Tentative excessive", "recipient_name": "Mariam Camara", "recipient_phone": "620000002"},
        headers=_auth(pharmacist),
    )
    assert over_refund.status_code == 400
