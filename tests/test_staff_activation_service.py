from datetime import datetime, timedelta

import pytest

import models
from services import staff_activation_service as service
from services.staff_activation_service import ActivationError


def _clinic_and_actor(db_session):
    from core.provisioning_context import provisioning_channel
    from security import hash_password

    clinic = models.Clinic(name="Clinique Invitation", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    with provisioning_channel("test_fixture"):
        actor = models.User(
            email=f"activation-admin-{clinic.id}@test.gn", hashed_password=hash_password("Secret12Pass!"),
            role="clinic_admin", clinic_id=clinic.id,
        )
        db_session.add(actor)
        db_session.commit()
    return clinic, actor


def test_invited_staff_is_inactive_until_single_use_activation(db_session, monkeypatch):
    clinic, actor = _clinic_and_actor(db_session)
    delivered = {}
    monkeypatch.setattr(service, "send_staff_activation_email", lambda email, link, **kwargs: delivered.update(email=email, link=link) or True)
    user, row, sent = service.invite_staff(
        db_session, actor_id=actor.id, clinic_id=clinic.id,
        email=f"new-nurse-{clinic.id}@test.gn", role="nurse", first_name="Aïssatou", last_name="Diallo",
    )
    assert sent is True and row.delivery_status == "sent"
    assert user.is_active is False and user.email_verified_at is None
    assert "token=" in delivered["link"]
    assert db_session.query(models.ClinicStaff).filter_by(user_id=user.id).one().is_active is False

    raw = delivered["link"].split("token=", 1)[1]
    inspected = service.inspect_activation(db_session, raw)
    assert inspected["clinic_name"] == clinic.name
    activated = service.complete_activation(db_session, token=raw, password="SafeClinicPass12!")
    assert activated.is_active is True and activated.email_verified_at is not None
    assert db_session.query(models.ClinicStaff).filter_by(user_id=user.id).one().is_active is True
    with pytest.raises(ActivationError):
        service.complete_activation(db_session, token=raw, password="AnotherSafePass12!")


def test_resend_revokes_previous_link_and_expired_link_fails(db_session, monkeypatch):
    clinic, actor = _clinic_and_actor(db_session)
    links = []
    monkeypatch.setattr(service, "send_staff_activation_email", lambda email, link, **kwargs: links.append(link) or True)
    user, first, _ = service.invite_staff(
        db_session, actor_id=actor.id, clinic_id=clinic.id,
        email=f"new-lab-{clinic.id}@test.gn", role="lab_technician", first_name="Mamadou", last_name="Bah",
    )
    second, _ = service.resend_invitation(db_session, actor_id=actor.id, user=user)
    db_session.refresh(first)
    assert first.revoked_at is not None and second.id != first.id
    with pytest.raises(ActivationError):
        service.inspect_activation(db_session, links[0].split("token=", 1)[1])
    second.expires_at = datetime.utcnow() - timedelta(seconds=1)
    db_session.commit()
    with pytest.raises(ActivationError):
        service.inspect_activation(db_session, links[1].split("token=", 1)[1])


def test_delivery_failure_never_activates_account(db_session, monkeypatch):
    clinic, actor = _clinic_and_actor(db_session)
    monkeypatch.setattr(service, "send_staff_activation_email", lambda *args, **kwargs: False)
    user, row, sent = service.invite_staff(
        db_session, actor_id=actor.id, clinic_id=clinic.id,
        email=f"failed-invite-{clinic.id}@test.gn", role="receptionist", first_name="Mariama", last_name="Camara",
    )
    assert sent is False and row.delivery_status == "failed" and user.is_active is False

