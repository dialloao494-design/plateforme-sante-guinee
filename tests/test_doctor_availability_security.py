"""
Security tests for R2 — doctor availability IDOR (cross-practitioner schedule mutation).

Verifies that doctors cannot create, update, or deactivate another doctor's
availability slots. Administrators retain legitimate cross-doctor management.
"""

from __future__ import annotations

import uuid
from datetime import time

import pytest

from models.availability import DoctorAvailability
from models.doctor import Doctor
from security import create_access_token
from services.user_provisioning import create_admin_user, register_public_user


def _auth_headers(user) -> dict[str, str]:
    token = create_access_token({"sub": user.email, "user_id": user.id, "user_role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def two_doctors_context(db_session):
    suffix = uuid.uuid4().hex[:8]
    doctor_a_user = register_public_user(
        db_session, email=f"dr.a.{suffix}@test.gn", password="Secret12Pass!", role="doctor"
    ).user
    doctor_b_user = register_public_user(
        db_session, email=f"dr.b.{suffix}@test.gn", password="Secret12Pass!", role="doctor"
    ).user
    doctor_a = db_session.query(Doctor).filter(Doctor.user_id == doctor_a_user.id).first()
    doctor_b = db_session.query(Doctor).filter(Doctor.user_id == doctor_b_user.id).first()

    slot_b = DoctorAvailability(
        doctor_id=doctor_b.id,
        day_of_week=2,
        start_time=time(9, 0),
        end_time=time(17, 0),
        is_active=True,
    )
    db_session.add(slot_b)
    db_session.commit()
    db_session.refresh(slot_b)

    admin = create_admin_user(
        db_session,
        email=f"admin.avail.{suffix}@test.gn",
        password="AdminPass12!",
        channel="test_fixture",
    ).user

    return {
        "doctor_a": doctor_a,
        "doctor_b": doctor_b,
        "doctor_a_user": doctor_a_user,
        "doctor_b_user": doctor_b_user,
        "slot_b": slot_b,
        "admin_user": admin,
        "doctor_a_headers": _auth_headers(doctor_a_user),
        "doctor_b_headers": _auth_headers(doctor_b_user),
        "admin_headers": _auth_headers(admin),
    }


def _create_payload(doctor_id: int, day: int = 1) -> dict:
    return {
        "doctor_id": doctor_id,
        "day_of_week": day,
        "start_time": "08:00:00",
        "end_time": "12:00:00",
    }


class TestCrossDoctorAvailabilityBlocked:
    def test_doctor_cannot_create_slot_for_peer(self, client, two_doctors_context):
        ctx = two_doctors_context
        response = client.post(
            f"/doctors/{ctx['doctor_b'].id}/availability",
            json=_create_payload(ctx["doctor_b"].id, day=3),
            headers=ctx["doctor_a_headers"],
        )
        assert response.status_code == 403

    def test_doctor_cannot_update_peer_slot(self, client, two_doctors_context):
        ctx = two_doctors_context
        response = client.put(
            f"/doctors/{ctx['doctor_b'].id}/availability/{ctx['slot_b'].id}",
            json={"start_time": "06:00:00", "end_time": "08:00:00"},
            headers=ctx["doctor_a_headers"],
        )
        assert response.status_code == 403

    def test_doctor_cannot_delete_peer_slot(self, client, two_doctors_context):
        ctx = two_doctors_context
        response = client.delete(
            f"/doctors/{ctx['doctor_b'].id}/availability/{ctx['slot_b'].id}",
            headers=ctx["doctor_a_headers"],
        )
        assert response.status_code == 403

    def test_patient_cannot_create_slot(self, client, db_session, two_doctors_context):
        ctx = two_doctors_context
        patient = register_public_user(
            db_session, email=f"pat.avail.{uuid.uuid4().hex[:6]}@test.gn", password="Secret12Pass!", role="patient"
        ).user
        response = client.post(
            f"/doctors/{ctx['doctor_b'].id}/availability",
            json=_create_payload(ctx["doctor_b"].id, day=4),
            headers=_auth_headers(patient),
        )
        assert response.status_code == 403


class TestOwnScheduleAllowed:
    def test_doctor_can_create_own_slot(self, client, two_doctors_context):
        ctx = two_doctors_context
        response = client.post(
            f"/doctors/{ctx['doctor_a'].id}/availability",
            json=_create_payload(ctx["doctor_a"].id, day=1),
            headers=ctx["doctor_a_headers"],
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["doctor_id"] == ctx["doctor_a"].id

    def test_doctor_can_update_own_slot(self, client, db_session, two_doctors_context):
        ctx = two_doctors_context
        slot_a = DoctorAvailability(
            doctor_id=ctx["doctor_a"].id,
            day_of_week=0,
            start_time=time(10, 0),
            end_time=time(18, 0),
            is_active=True,
        )
        db_session.add(slot_a)
        db_session.commit()
        db_session.refresh(slot_a)

        response = client.put(
            f"/doctors/{ctx['doctor_a'].id}/availability/{slot_a.id}",
            json={"start_time": "11:00:00"},
            headers=ctx["doctor_a_headers"],
        )
        assert response.status_code == 200
        assert response.json()["start_time"].startswith("11:00")

    def test_doctor_can_deactivate_own_slot(self, client, db_session, two_doctors_context):
        ctx = two_doctors_context
        slot_a = DoctorAvailability(
            doctor_id=ctx["doctor_a"].id,
            day_of_week=5,
            start_time=time(9, 0),
            end_time=time(12, 0),
            is_active=True,
        )
        db_session.add(slot_a)
        db_session.commit()
        db_session.refresh(slot_a)

        response = client.delete(
            f"/doctors/{ctx['doctor_a'].id}/availability/{slot_a.id}",
            headers=ctx["doctor_a_headers"],
        )
        assert response.status_code == 200


class TestAdminCrossDoctorManagement:
    def test_admin_can_create_slot_for_any_doctor(self, client, two_doctors_context):
        ctx = two_doctors_context
        response = client.post(
            f"/doctors/{ctx['doctor_b'].id}/availability",
            json=_create_payload(ctx["doctor_b"].id, day=6),
            headers=ctx["admin_headers"],
        )
        assert response.status_code == 200

    def test_admin_can_update_any_doctor_slot(self, client, two_doctors_context):
        ctx = two_doctors_context
        response = client.put(
            f"/doctors/{ctx['doctor_b'].id}/availability/{ctx['slot_b'].id}",
            json={"end_time": "18:00:00"},
            headers=ctx["admin_headers"],
        )
        assert response.status_code == 200

    def test_admin_can_deactivate_any_doctor_slot(self, client, db_session, two_doctors_context):
        ctx = two_doctors_context
        slot = DoctorAvailability(
            doctor_id=ctx["doctor_a"].id,
            day_of_week=4,
            start_time=time(8, 0),
            end_time=time(16, 0),
            is_active=True,
        )
        db_session.add(slot)
        db_session.commit()
        db_session.refresh(slot)

        response = client.delete(
            f"/doctors/{ctx['doctor_a'].id}/availability/{slot.id}",
            headers=ctx["admin_headers"],
        )
        assert response.status_code == 200


class TestReadAccessUnchanged:
    def test_patient_can_read_doctor_availability(self, client, db_session, two_doctors_context):
        ctx = two_doctors_context
        patient = register_public_user(
            db_session, email=f"read.pat.{uuid.uuid4().hex[:6]}@test.gn", password="Secret12Pass!", role="patient"
        ).user
        response = client.get(
            f"/doctors/{ctx['doctor_b'].id}/availability",
            headers=_auth_headers(patient),
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


class TestDoctorOwnershipPolicyUnit:
    def test_policy_blocks_cross_doctor_mutation(self, db_session, two_doctors_context):
        from core.doctor_ownership_policy import DoctorOwnershipPolicy

        with pytest.raises(Exception) as exc:
            DoctorOwnershipPolicy.assert_can_mutate_doctor_resource(
                db_session,
                target_doctor_id=two_doctors_context["doctor_b"].id,
                current_user=two_doctors_context["doctor_a_user"],
            )
        assert getattr(exc.value, "status_code", None) == 403

    def test_policy_allows_admin(self, db_session, two_doctors_context):
        from core.doctor_ownership_policy import DoctorOwnershipPolicy

        result = DoctorOwnershipPolicy.assert_can_mutate_doctor_resource(
            db_session,
            target_doctor_id=two_doctors_context["doctor_b"].id,
            current_user=two_doctors_context["admin_user"],
        )
        assert result is None
