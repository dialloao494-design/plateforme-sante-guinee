"""Clinical reporting API."""

from __future__ import annotations

import uuid
from datetime import date, timedelta

import models
from security import create_access_token, hash_password
from core.provisioning_context import provisioning_channel


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {"sub": user.email, "user_id": user.id, "user_role": user.role, "role": user.role}
    )
    return {"Authorization": f"Bearer {token}"}


def test_clinical_reports_summary_and_csv(client, db_session, admin_user):
    suffix = uuid.uuid4().hex[:8]
    r = client.post(
        "/clinical/clinics",
        json={"name": f"Rep Clinic {suffix}", "city": "Conakry"},
        headers=_auth(admin_user),
    )
    clinic_id = r.json()["id"]
    admin_user.clinic_id = clinic_id
    db_session.add(models.ClinicStaff(clinic_id=clinic_id, user_id=admin_user.id, is_active=True))
    with provisioning_channel("test_fixture"):
        reception = models.User(
            email=f"rep.reception.{suffix}@test.com",
            hashed_password=hash_password("StaffPass1"),
            role="receptionist",
            clinic_id=clinic_id,
        )
        db_session.add(reception)
        db_session.commit()
        db_session.refresh(reception)

    start = (date.today() - timedelta(days=30)).isoformat()
    end = date.today().isoformat()
    r = client.get(
        "/clinical/reports/summary",
        params={"start": start, "end": end},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert "revenue" in r.json()

    r = client.get(
        "/clinical/reports/export.csv",
        params={"start": start, "end": end},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert "Rapport clinique" in r.text

    r = client.get(
        "/clinical/reports/export.pdf",
        params={"start": start, "end": end},
        headers=_auth(reception),
    )
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
