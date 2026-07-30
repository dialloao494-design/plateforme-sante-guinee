"""
Security tests for R1 — teleconsultation meeting_link bypass (pre-payment exposure).

Verifies that join URLs are never published before treasury settlement and that
Jitsi credentials are only issued via authenticated /teleconsultation/.../access.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta

import pytest

from core.teleconsult_exposure_policy import TeleconsultExposurePolicy
from models.doctor import Doctor
from models.patient import Patient
from models.rendezvous import RendezVous
from security import create_access_token
from services.payment_settlement import PaymentSettlementService
from services.rendezvous_service import RendezVousService
from services.teleconsult_room import jitsi_embed_mode, meeting_link_for_appointment, room_name
from services.teleconsultation_access import validate_teleconsult_access
from tests.clinic_fixtures import bind_clinic_booking
from services.user_provisioning import register_public_user


@pytest.fixture()
def payment_stub_env(monkeypatch):
    monkeypatch.setenv("ALLOW_STUB_PAYMENT", "true")
    monkeypatch.setenv("PAYMENT_STUB_TOKEN", "pytest-payment-stub-secret")
    monkeypatch.setenv("ENVIRONMENT", "development")
    from core.settings import get_settings

    get_settings.cache_clear()


def _auth_headers(user) -> dict[str, str]:
    token = create_access_token({"sub": user.email, "user_id": user.id, "user_role": user.role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def teleconsult_booking(db_session, client):
    suffix = uuid.uuid4().hex[:8]
    patient_user = register_public_user(
        db_session, email=f"tc.patient.{suffix}@test.gn", password="Secret12Pass!", role="patient"
    ).user
    patient = db_session.query(Patient).filter(Patient.user_id == patient_user.id).first()
    doctor_user = register_public_user(
        db_session, email=f"tc.doctor.{suffix}@test.gn", password="Secret12Pass!", role="doctor"
    ).user
    doctor = db_session.query(Doctor).filter(Doctor.user_id == doctor_user.id).first()
    clinic = bind_clinic_booking(db_session, doctor=doctor, patient=patient)

    start = datetime.now() + timedelta(minutes=10)
    rdv = RendezVous(
        date=start,
        duration_minutes=30,
        patient_id=patient.id,
        doctor_id=doctor.id,
        clinic_id=clinic.id,
        status="pending",
        payment_status="unpaid",
        price=float(doctor.consultation_fee or 50000),
        consultation_type="teleconsultation",
    )
    db_session.add(rdv)
    db_session.commit()
    db_session.refresh(rdv)

    return {
        "patient_user": patient_user,
        "doctor_user": doctor_user,
        "patient": patient,
        "doctor": doctor,
        "appointment": rdv,
        "patient_headers": _auth_headers(patient_user),
        "doctor_headers": _auth_headers(doctor_user),
    }


class TestMeetingLinkNotCreatedBeforePayment:
    def test_create_teleconsult_does_not_persist_meeting_link(
        self, db_session, teleconsult_booking
    ):
        rdv = teleconsult_booking["appointment"]
        assert rdv.consultation_type == "teleconsultation"
        assert rdv.meeting_link is None

    def test_legacy_meeting_link_stripped_from_api_response(
        self, client, db_session, teleconsult_booking
    ):
        rdv = teleconsult_booking["appointment"]
        legacy_url = meeting_link_for_appointment(rdv.id)
        rdv.meeting_link = legacy_url
        db_session.commit()

        response = client.get(
            f"/appointments/{rdv.id}",
            headers=teleconsult_booking["patient_headers"],
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("meeting_link") is None
        assert room_name(rdv.id) in legacy_url


class TestAppointmentApiNeverExposesJoinUrl:
    def test_unpaid_appointment_list_has_no_meeting_link(self, client, teleconsult_booking):
        rdv = teleconsult_booking["appointment"]
        response = client.get("/appointments/", headers=teleconsult_booking["patient_headers"])
        assert response.status_code == 200
        rows = response.json()
        match = next(r for r in rows if r["id"] == rdv.id)
        assert match.get("meeting_link") is None

    def test_paid_appointment_still_hides_meeting_link(
        self, client, db_session, teleconsult_booking, payment_stub_env
    ):
        from core.payment_policy import SETTLEMENT_CHANNEL_DEV_STUB

        rdv = teleconsult_booking["appointment"]
        PaymentSettlementService.settle_appointment(
            db_session,
            rdv.id,
            channel=SETTLEMENT_CHANNEL_DEV_STUB,
            stub_token=os.environ["PAYMENT_STUB_TOKEN"],
        )
        db_session.expire_all()

        response = client.get(
            f"/appointments/{rdv.id}",
            headers=teleconsult_booking["patient_headers"],
        )
        assert response.status_code == 200
        assert response.json().get("meeting_link") is None


class TestTeleconsultAccessPaymentGate:
    def test_access_endpoint_blocked_before_payment(self, client, teleconsult_booking):
        rdv = teleconsult_booking["appointment"]
        response = client.get(
            f"/teleconsultation/appointments/{rdv.id}/access",
            headers=teleconsult_booking["patient_headers"],
        )
        assert response.status_code == 403

    def test_access_endpoint_issues_credentials_after_payment(
        self, client, db_session, teleconsult_booking, payment_stub_env
    ):
        from core.payment_policy import SETTLEMENT_CHANNEL_DEV_STUB

        rdv = teleconsult_booking["appointment"]
        PaymentSettlementService.settle_appointment(
            db_session,
            rdv.id,
            channel=SETTLEMENT_CHANNEL_DEV_STUB,
            stub_token=os.environ["PAYMENT_STUB_TOKEN"],
        )
        db_session.expire_all()

        response = client.get(
            f"/teleconsultation/appointments/{rdv.id}/access",
            headers=teleconsult_booking["patient_headers"],
        )
        assert response.status_code == 200, response.text
        payload = response.json()
        assert payload.get("meeting_url")
        assert payload.get("room_name") == room_name(rdv.id)
        assert payload["room_name"] in payload["meeting_url"]

    def test_room_status_never_includes_meeting_url(
        self, client, db_session, teleconsult_booking, payment_stub_env
    ):
        from core.payment_policy import SETTLEMENT_CHANNEL_DEV_STUB

        rdv = teleconsult_booking["appointment"]
        PaymentSettlementService.settle_appointment(
            db_session,
            rdv.id,
            channel=SETTLEMENT_CHANNEL_DEV_STUB,
            stub_token=os.environ["PAYMENT_STUB_TOKEN"],
        )
        response = client.get(
            f"/teleconsultation/appointments/{rdv.id}/room-status",
            headers=teleconsult_booking["patient_headers"],
        )
        assert response.status_code == 200
        body = response.json()
        assert body.get("meeting_url") is None


class TestTeleconsultExposurePolicy:
    def test_may_issue_join_credentials_requires_payment(self, db_session, teleconsult_booking):
        rdv = teleconsult_booking["appointment"]
        assert TeleconsultExposurePolicy.may_issue_join_credentials(rdv) is False

        rdv.payment_status = "paid"
        rdv.status = "confirmed"
        assert TeleconsultExposurePolicy.may_issue_join_credentials(rdv) is True

    def test_unpaid_access_payload_has_no_meeting_url(self, db_session, teleconsult_booking):
        from unittest.mock import MagicMock

        from services.teleconsultation_access import _build_access_payload

        rdv = teleconsult_booking["appointment"]
        user = MagicMock(id=teleconsult_booking["patient_user"].id, email="p@test.gn", role="patient")
        now = datetime.now()
        open_at = now - timedelta(minutes=5)
        close_at = now + timedelta(hours=1)
        payload = _build_access_payload(
            rdv,
            user,
            "patient",
            now=now,
            open_at=open_at,
            close_at=close_at,
            include_credentials=True,
        )
        assert payload["meeting_url"] is None
        assert payload["jitsi_jwt"] is None


class TestProductionJitsiHardening:
    def test_deployed_environment_blocks_open_jitsi_without_jwt(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "production")
        monkeypatch.delenv("JITSI_APP_ID", raising=False)
        monkeypatch.delenv("JITSI_APP_SECRET", raising=False)
        monkeypatch.delenv("JITSI_PRIVATE_KEY", raising=False)
        monkeypatch.delenv("ALLOW_OPEN_JITSI_IN_PRODUCTION", raising=False)
        monkeypatch.setenv("JITSI_DOMAIN", "jitsi.example.com")
        from core.settings import get_settings

        get_settings.cache_clear()
        assert jitsi_embed_mode() == "blocked"

    def test_development_allows_open_jitsi_for_local_testing(self, monkeypatch):
        monkeypatch.setenv("ENVIRONMENT", "development")
        monkeypatch.delenv("JITSI_APP_ID", raising=False)
        monkeypatch.delenv("JITSI_APP_SECRET", raising=False)
        monkeypatch.setenv("JITSI_DOMAIN", "127.0.0.1:8443")
        from core.settings import get_settings

        get_settings.cache_clear()
        assert jitsi_embed_mode() == "self_hosted_open"


class TestRefundClearsMeetingLink:
    def test_full_refund_clears_stored_meeting_link(
        self, db_session, teleconsult_booking, payment_stub_env
    ):
        from core.payment_policy import SETTLEMENT_CHANNEL_DEV_STUB
        from services.payment_refunds import PaymentRefundService

        rdv = teleconsult_booking["appointment"]
        settled = PaymentSettlementService.settle_appointment(
            db_session,
            rdv.id,
            channel=SETTLEMENT_CHANNEL_DEV_STUB,
            stub_token=os.environ["PAYMENT_STUB_TOKEN"],
        )
        settled.meeting_link = meeting_link_for_appointment(rdv.id)
        db_session.commit()

        PaymentRefundService.apply_refund(
            db_session,
            payment_intent_id=settled.payment_intent_id,
            amount_refunded_cents=5000000,
            amount_total_cents=5000000,
        )
        db_session.expire_all()
        refreshed = db_session.query(RendezVous).filter(RendezVous.id == rdv.id).first()
        assert refreshed.meeting_link is None
        assert refreshed.payment_status == "refunded"
