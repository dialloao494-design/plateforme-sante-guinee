"""
Payment access policy enforcement — cross-cutting bypass regression tests.

Covers audit findings F1–F4: teleconsultation gate, appointment routes alignment,
no pending-based access, post-refund revocation.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from core.payment_access_policy import PaymentAccessPolicy
from models.doctor import Doctor
from models.patient import Patient
from models.rendezvous import RendezVous
from services.payment_refunds import PaymentRefundService
from services.rendezvous_service import RendezVousService
from services.teleconsultation_access import evaluate_teleconsult_room, validate_teleconsult_access
from services.user_provisioning import register_public_user


@pytest.fixture()
def payment_stub_env(monkeypatch):
    monkeypatch.setenv("ALLOW_STUB_PAYMENT", "true")
    monkeypatch.setenv("PAYMENT_STUB_TOKEN", "pytest-payment-stub-secret")
    monkeypatch.setenv("ENVIRONMENT", "development")
    from core.settings import get_settings

    get_settings.cache_clear()


def _tele_user(role: str, user_id: int = 1):
    u = MagicMock()
    u.id = user_id
    u.role = role
    u.email = f"{role}@test.com"
    return u


def _tele_appointment(**kwargs):
    a = MagicMock()
    a.id = kwargs.get("id", 42)
    a.consultation_type = kwargs.get("consultation_type", "teleconsultation")
    a.status = kwargs.get("status", "confirmed")
    a.payment_status = kwargs.get("payment_status", "paid")
    a.date = kwargs.get("date", datetime.now() + timedelta(minutes=10))
    a.duration_minutes = kwargs.get("duration_minutes", 30)
    a.meeting_link = kwargs.get("meeting_link", None)
    a.doctor_id = kwargs.get("doctor_id", 10)
    a.patient_id = kwargs.get("patient_id", 20)
    return a


def _tele_db(appointment, doctor=None, patient=None):
    db = MagicMock()

    def query(model):
        q = MagicMock()
        if model.__name__ == "RendezVous":
            q.filter.return_value.first.return_value = appointment
        elif model.__name__ == "Doctor" and doctor is not None:
            q.filter.return_value.first.return_value = doctor
        elif model.__name__ == "Patient" and patient is not None:
            q.filter.return_value.first.return_value = patient
        else:
            q.filter.return_value.first.return_value = None
        return q

    db.query.side_effect = query
    return db


class TestTeleconsultPaymentGate:
    def test_unpaid_confirmed_allowed_without_online_payment(self):
        appt = _tele_appointment(status="confirmed", payment_status="unpaid")
        db = _tele_db(appt, patient=MagicMock(id=20, user_id=1))
        result = validate_teleconsult_access(42, _tele_user("patient", 1), db)
        assert result["can_join"] is True

    def test_pending_unpaid_blocked_even_in_time_window(self):
        appt = _tele_appointment(status="pending", payment_status="unpaid")
        db = _tele_db(appt, doctor=MagicMock(id=10, user_id=1))
        result = evaluate_teleconsult_room(42, _tele_user("doctor"), db)
        assert result["can_join"] is False
        assert result["reason"] == "status_blocked"

    def test_pending_paid_blocked_no_pending_access(self):
        appt = _tele_appointment(status="pending", payment_status="paid")
        db = _tele_db(appt, doctor=MagicMock(id=10, user_id=1))
        result = evaluate_teleconsult_room(42, _tele_user("doctor"), db)
        assert result["can_join"] is False
        assert result["reason"] == "status_blocked"

    def test_confirmed_paid_allowed(self):
        appt = _tele_appointment(status="confirmed", payment_status="paid")
        db = _tele_db(appt, doctor=MagicMock(id=10, user_id=1))
        result = validate_teleconsult_access(42, _tele_user("doctor"), db)
        assert result["can_join"] is True

    def test_refunded_revokes_access_immediately(self):
        appt = _tele_appointment(status="confirmed", payment_status="refunded")
        db = _tele_db(appt, patient=MagicMock(id=20, user_id=1))
        with pytest.raises(HTTPException) as exc:
            validate_teleconsult_access(42, _tele_user("patient", 1), db)
        assert exc.value.status_code == 403
        assert "rembours" in exc.value.detail.lower()

    def test_partial_refund_revokes_access(self):
        appt = _tele_appointment(status="confirmed", payment_status="partially_refunded")
        db = _tele_db(appt, patient=MagicMock(id=20, user_id=1))
        result = evaluate_teleconsult_room(42, _tele_user("patient", 1), db)
        assert result["can_join"] is False
        assert result["reason"] == "payment_revoked"


class TestAppointmentStatusAlignment:
    @pytest.fixture()
    def unpaid_pending(self, db_session, payment_stub_env):
        suffix = os.urandom(4).hex()
        patient_user = register_public_user(
            db_session,
            email=f"access.patient.{suffix}@test.gn",
            password="secret12",
            role="patient",
        ).user
        patient = db_session.query(Patient).filter(Patient.user_id == patient_user.id).first()
        doctor_user = register_public_user(
            db_session,
            email=f"access.doctor.{suffix}@test.gn",
            password="secret12",
            role="doctor",
        ).user
        doctor = db_session.query(Doctor).filter(Doctor.user_id == doctor_user.id).first()
        rdv = RendezVous(
            date=datetime.utcnow() + timedelta(days=2),
            duration_minutes=30,
            patient_id=patient.id,
            doctor_id=doctor.id,
            status="pending",
            payment_status="unpaid",
            price=50000.0,
            consultation_type="physical",
        )
        db_session.add(rdv)
        db_session.commit()
        db_session.refresh(rdv)
        return rdv

    def test_doctor_can_confirm_unpaid_pending(self, db_session, unpaid_pending):
        updated = RendezVousService.update_appointment_status(
            unpaid_pending.id, "confirmed", db_session
        )
        assert updated.status == "confirmed"
        assert updated.payment_status == "unpaid"

    def test_cannot_set_status_paid_without_treasury(self, db_session, unpaid_pending):
        with pytest.raises(HTTPException) as exc:
            RendezVousService.update_appointment_status(
                unpaid_pending.id, "paid", db_session
            )
        assert exc.value.status_code in {400, 403}

    def test_doctor_can_confirm_after_payment(self, db_session, unpaid_pending, payment_stub_env):
        from core.payment_policy import SETTLEMENT_CHANNEL_DEV_STUB
        from services.payment_settlement import PaymentSettlementService

        PaymentSettlementService.settle_appointment(
            db_session,
            unpaid_pending.id,
            channel=SETTLEMENT_CHANNEL_DEV_STUB,
            stub_token=os.environ["PAYMENT_STUB_TOKEN"],
        )
        db_session.expire_all()
        rdv = db_session.query(RendezVous).filter(RendezVous.id == unpaid_pending.id).first()
        assert rdv.payment_status == "paid"
        assert rdv.status == "confirmed"

    def test_doctor_put_confirm_unpaid_allowed(
        self, client, db_session, payment_stub_env, unpaid_pending
    ):
        from models.user import User

        doctor = db_session.query(Doctor).filter(Doctor.id == unpaid_pending.doctor_id).first()
        doctor_user = db_session.query(User).filter(User.id == doctor.user_id).first()

        login = client.post(
            "/auth/login-json",
            json={"email": doctor_user.email, "password": "secret12"},
        )
        assert login.status_code == 200, login.text
        headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

        response = client.put(
            f"/appointments/{unpaid_pending.id}/",
            json={"status": "confirmed"},
            headers=headers,
        )
        assert response.status_code == 200

        db_session.expire_all()
        rdv = db_session.query(RendezVous).filter(RendezVous.id == unpaid_pending.id).first()
        assert rdv.status == "confirmed"


class TestRefundRevokesTeleconsultAccess:
    def test_full_refund_blocks_subsequent_access(self, db_session, payment_stub_env):
        from core.payment_policy import SETTLEMENT_CHANNEL_DEV_STUB
        from services.payment_settlement import PaymentSettlementService

        patient_user = register_public_user(
            db_session, email="refund.patient@test.gn", password="secret12", role="patient"
        ).user
        patient = db_session.query(Patient).filter(Patient.user_id == patient_user.id).first()
        doctor_user = register_public_user(
            db_session, email="refund.doctor@test.gn", password="secret12", role="doctor"
        ).user
        doctor = db_session.query(Doctor).filter(Doctor.user_id == doctor_user.id).first()
        rdv = RendezVous(
            date=datetime.utcnow() + timedelta(minutes=15),
            duration_minutes=30,
            patient_id=patient.id,
            doctor_id=doctor.id,
            status="pending",
            payment_status="unpaid",
            price=50.0,
            consultation_type="teleconsultation",
        )
        db_session.add(rdv)
        db_session.commit()
        db_session.refresh(rdv)

        settled = PaymentSettlementService.settle_appointment(
            db_session,
            rdv.id,
            channel=SETTLEMENT_CHANNEL_DEV_STUB,
            stub_token=os.environ["PAYMENT_STUB_TOKEN"],
        )
        assert settled.payment_status == "paid"

        appt = _tele_appointment(
            id=rdv.id,
            status=settled.status,
            payment_status=settled.payment_status,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )
        db = _tele_db(appt, patient=MagicMock(id=patient.id, user_id=patient_user.id))
        validate_teleconsult_access(rdv.id, _tele_user("patient", patient_user.id), db)

        PaymentRefundService.apply_refund(
            db_session,
            payment_intent_id=settled.payment_intent_id,
            amount_refunded_cents=5000,
            amount_total_cents=5000,
        )
        db_session.expire_all()
        refunded = db_session.query(RendezVous).filter(RendezVous.id == rdv.id).first()
        assert refunded.payment_status == "refunded"

        appt_refunded = _tele_appointment(
            id=refunded.id,
            status=refunded.status,
            payment_status=refunded.payment_status,
            doctor_id=doctor.id,
            patient_id=patient.id,
        )
        db2 = _tele_db(appt_refunded, patient=MagicMock(id=patient.id, user_id=patient_user.id))
        with pytest.raises(HTTPException) as exc:
            validate_teleconsult_access(rdv.id, _tele_user("patient", patient_user.id), db2)
        assert exc.value.status_code == 403


class TestPaymentAccessPolicyUnit:
    def test_pending_not_business_active(self):
        appt = MagicMock(status="pending", payment_status="paid")
        assert PaymentAccessPolicy.is_business_active_status(appt) is False

    def test_treasury_cleared_requires_paid_payment_status(self):
        appt = MagicMock(status="confirmed", payment_status="unpaid")
        assert PaymentAccessPolicy.is_treasury_cleared(appt) is False
