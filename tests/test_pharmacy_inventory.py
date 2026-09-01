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
