"""
Security tests for admin manual payment settlement (clinic reception billing is separate).
"""

from __future__ import annotations

import pytest

from models.doctor import Doctor
from models.patient import Patient
from models.rendezvous import RendezVous
from services.user_provisioning import register_public_user


@pytest.fixture()
def payment_stub_env(monkeypatch):
    monkeypatch.setenv("ALLOW_STUB_PAYMENT", "true")
    monkeypatch.setenv("PAYMENT_STUB_TOKEN", "pytest-payment-stub-secret")
    monkeypatch.setenv("ENVIRONMENT", "development")


def _ensure_user(db_session, email: str, role: str):
    from models.user import User

    existing = db_session.query(User).filter(User.email == email).first()
    if existing:
        return existing
    return register_public_user(db_session, email=email, password="secret12", role=role).user


@pytest.fixture()
def patient_with_pending_appointment(db_session, payment_stub_env):
    from datetime import datetime, timedelta
    import uuid

    suffix = uuid.uuid4().hex[:8]
    user = _ensure_user(db_session, f"patient.pay.{suffix}@test.gn", "patient")
    patient = db_session.query(Patient).filter(Patient.user_id == user.id).first()

    doctor_user = _ensure_user(db_session, f"doctor.pay.{suffix}@test.gn", "doctor")
    doctor = db_session.query(Doctor).filter(Doctor.user_id == doctor_user.id).first()

    rdv = RendezVous(
        date=datetime.utcnow() + timedelta(days=2),
        duration_minutes=30,
        patient_id=patient.id,
        doctor_id=doctor.id,
        status="pending",
        payment_status="unpaid",
        price=45000.0,
        consultation_type="physical",
    )
    db_session.add(rdv)
    db_session.commit()
    db_session.refresh(rdv)
    return {"user": user, "patient": patient, "appointment": rdv, "password": "secret12"}


@pytest.fixture()
def patient_headers(client, payment_stub_env, patient_with_pending_appointment):
    email = patient_with_pending_appointment["user"].email
    password = patient_with_pending_appointment["password"]
    login = client.post(
        "/auth/login-json",
        json={"email": email, "password": password},
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


class TestRendezvousConfirmPayment:
    def test_patient_cannot_use_rendezvous_confirm_payment(
        self, client, patient_headers, patient_with_pending_appointment
    ):
        aid = patient_with_pending_appointment["appointment"].id
        response = client.post(
            f"/rendezvous/{aid}/confirm-payment",
            headers=patient_headers,
        )
        assert response.status_code == 403

    def test_no_paid_state_after_blocked_confirm(
        self, client, db_session, patient_headers, patient_with_pending_appointment
    ):
        aid = patient_with_pending_appointment["appointment"].id
        client.post(f"/rendezvous/{aid}/confirm-payment", headers=patient_headers)
        db_session.expire_all()
        rdv = db_session.query(RendezVous).filter(RendezVous.id == aid).first()
        assert rdv.payment_status != "paid"
        assert rdv.status != "confirmed"

    def test_admin_can_settle_via_rendezvous_confirm(
        self, client, admin_headers, db_session, patient_with_pending_appointment
    ):
        aid = patient_with_pending_appointment["appointment"].id
        response = client.post(
            f"/rendezvous/{aid}/confirm-payment",
            headers=admin_headers,
        )
        assert response.status_code == 200
        db_session.expire_all()
        rdv = db_session.query(RendezVous).filter(RendezVous.id == aid).first()
        assert rdv.status == "confirmed"
        assert rdv.payment_status == "paid"


class TestSettlementService:
    def test_direct_settle_without_channel_evidence_blocked(self, db_session, payment_stub_env):
        from services.payment_settlement import PaymentSettlementService
        from core.payment_policy import SETTLEMENT_CHANNEL_DEV_STUB

        provisioned = register_public_user(
            db_session,
            email="direct.settle@test.gn",
            password="secret12",
            role="patient",
        )
        patient = db_session.query(Patient).filter(Patient.user_id == provisioned.user.id).first()
        doctor_user = register_public_user(
            db_session,
            email="doc.settle@test.gn",
            password="secret12",
            role="doctor",
        )
        doctor = db_session.query(Doctor).filter(Doctor.user_id == doctor_user.user.id).first()
        from datetime import datetime, timedelta

        rdv = RendezVous(
            date=datetime.utcnow() + timedelta(days=1),
            duration_minutes=30,
            patient_id=patient.id,
            doctor_id=doctor.id,
            status="pending",
            payment_status="unpaid",
            price=10000.0,
            consultation_type="physical",
        )
        db_session.add(rdv)
        db_session.commit()

        with pytest.raises(Exception) as exc:
            PaymentSettlementService.settle_appointment(
                db_session,
                rdv.id,
                channel=SETTLEMENT_CHANNEL_DEV_STUB,
                stub_token="bad",
            )
        assert getattr(exc.value, "status_code", None) == 403
