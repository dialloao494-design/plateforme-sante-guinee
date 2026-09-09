from models.authentication_event import AuthenticationEvent
from services.authentication_event_service import email_fingerprint


def _events(db_session):
    return db_session.query(AuthenticationEvent).order_by(AuthenticationEvent.id).all()


def test_login_outcomes_are_persisted_without_raw_email(client, db_session, admin_user):
    db_session.query(AuthenticationEvent).delete()
    db_session.commit()

    unknown = client.post(
        "/auth/login-json",
        json={"email": "Missing.User@Clinic.Test", "password": "NeverStored12!"},
        headers={"user-agent": "clinic-workstation/1", "x-request-id": "auth-request-1"},
    )
    wrong = client.post(
        "/auth/login-json",
        json={"email": admin_user.email.upper(), "password": "WrongPassword12!"},
        headers={"user-agent": "clinic-workstation/1", "x-request-id": "auth-request-2"},
    )
    success = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass12!"},
        headers={"user-agent": "clinic-workstation/1", "x-request-id": "auth-request-3"},
    )

    assert (unknown.status_code, wrong.status_code, success.status_code) == (401, 401, 200)
    events = _events(db_session)
    assert [(event.succeeded, event.reason) for event in events] == [
        (False, "user_not_found"),
        (False, "invalid_password"),
        (True, "success"),
    ]
    assert events[0].user_id is None
    assert events[1].user_id == admin_user.id
    assert events[2].user_id == admin_user.id
    assert events[1].email_fingerprint == events[2].email_fingerprint
    assert events[0].email_fingerprint == email_fingerprint("missing.user@clinic.test")
    assert events[2].user_agent == "clinic-workstation/1"
    assert events[2].request_id == "auth-request-3"
    assert not hasattr(events[2], "email")


def test_mfa_denial_is_not_recorded_as_success(client, db_session, admin_user):
    import pyotp

    from services.mfa_service import generate_mfa_secret

    db_session.query(AuthenticationEvent).delete()
    secret = generate_mfa_secret()
    admin_user.mfa_secret = secret
    admin_user.mfa_enabled = True
    db_session.add(admin_user)
    db_session.commit()

    denied = client.post(
        "/auth/login-json",
        json={"email": admin_user.email, "password": "AdminPass12!"},
    )
    accepted = client.post(
        "/auth/login-json",
        json={
            "email": admin_user.email,
            "password": "AdminPass12!",
            "mfa_code": pyotp.TOTP(secret).now(),
        },
    )

    assert denied.status_code == 401
    assert accepted.status_code == 200
    assert [(event.succeeded, event.reason) for event in _events(db_session)] == [
        (False, "mfa_required"),
        (True, "success"),
    ]

    admin_user.mfa_enabled = False
    admin_user.mfa_secret = None
    db_session.add(admin_user)
    db_session.commit()
