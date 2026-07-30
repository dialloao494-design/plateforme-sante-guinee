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
