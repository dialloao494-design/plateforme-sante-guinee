"""Opt-in concurrency regression against an isolated local synthetic PostgreSQL DB."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import os
from pathlib import Path
import time
import uuid

from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine import make_url


def _synthetic_engine():
    url = os.getenv("SYNTHETIC_POSTGRES_URL")
    if not url:
        pytest.skip("Requires a disposable local synthetic PostgreSQL database")
    parsed = make_url(url)
    # Never run this destructive fixture against remote or pre-existing app data.
    socket = parsed.query.get("host", "")
    assert parsed.database == "defensive_auth_synthetic"
    assert not parsed.host and str(Path(socket).resolve()).startswith("/private/tmp/defensive-auth-pg.")
    assert parsed.password is None
    return create_engine(url)


def test_refresh_waits_for_mfa_replacement_and_observes_revocation():
    engine = _synthetic_engine()
    from database import Base
    from models.user import User
    from models.refresh_token import RefreshToken
    from core.provisioning_context import provisioning_channel
    from security import hash_password
    from routers.auth import _lock_mfa_user
    from services.auth_session_service import issue_refresh_token, rotate_refresh_token, revoke_all_user_refresh_tokens

    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as seed:
        with provisioning_channel("test_fixture"):
            user = User(email=f"concurrency-{uuid.uuid4().hex}@example.test", role="patient",
                        hashed_password=hash_password("SyntheticPass456!"),
                        mfa_enabled=True, mfa_secret="synthetic-factor")
            seed.add(user)
            seed.commit()
        user_id = user.id
        raw, _ = issue_refresh_token(seed, user=user)

    pid = None
    outcome = None

    def refresh():
        nonlocal pid
        with Session() as session:
            pid = session.execute(text("SELECT pg_backend_pid()")).scalar_one()
            try:
                rotate_refresh_token(session, raw_token=raw)
                return "rotated"
            except HTTPException as exc:
                return exc.status_code

    try:
        with Session() as activation:
            user = activation.get(User, user_id)
            user = _lock_mfa_user(activation, user)
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(refresh)
                try:
                    # Observe a real server-side lock wait, not a timing guess.
                    deadline = time.monotonic() + 5
                    blocked = False
                    while time.monotonic() < deadline and not future.done():
                        with engine.connect() as observer:
                            if pid is not None:
                                blocked = observer.execute(text(
                                    "SELECT wait_event_type = 'Lock' AND query LIKE 'SELECT %' "
                                    "FROM pg_stat_activity WHERE pid=:pid"
                                ), {"pid": pid}).scalar() is True
                        if blocked:
                            break
                        time.sleep(0.01)
                    assert blocked, "Refresh did not wait for the MFA enrollment user lock"
                    user.mfa_secret = "synthetic-replacement-factor"
                    user.token_version = int(user.token_version or 0) + 1
                    revoke_all_user_refresh_tokens(activation, user_id=user_id, commit=False)
                    activation.commit()
                    outcome = future.result(timeout=5)
                finally:
                    # Release the lock before joining a worker on assertion failure.
                    activation.rollback()
        assert outcome == 401
        with Session() as check:
            assert check.query(RefreshToken).filter(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)).count() == 0
    finally:
        engine.dispose()


def test_administrator_revocation_uses_same_lock_order_as_refresh():
    engine = _synthetic_engine()
    from database import Base
    from models.user import User
    from models.clinic import Clinic
    from models.refresh_token import RefreshToken
    from core.provisioning_context import provisioning_channel
    from security import hash_password
    from routers.auth import _lock_mfa_user
    from services.auth_session_service import issue_refresh_token, rotate_refresh_token
    from services.staff_lifecycle_service import revoke_sessions
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    with Session() as seed:
        clinic = Clinic(name=f"Synthetic concurrency {uuid.uuid4().hex}")
        seed.add(clinic)
        seed.flush()
        clinic_id = clinic.id
        with provisioning_channel("test_fixture"):
            user = User(email=f"staff-{uuid.uuid4().hex}@example.test", role="receptionist",
                        clinic_id=clinic_id, hashed_password=hash_password("SyntheticPass456!"))
            actor = User(email=f"admin-{uuid.uuid4().hex}@example.test", role="platform_admin",
                         hashed_password=hash_password("SyntheticPass456!"))
            seed.add_all([user, actor])
            seed.commit()
        user_id, actor_id = user.id, actor.id
        raw, _ = issue_refresh_token(seed, user=user)
    pid = None

    def admin_revoke():
        nonlocal pid
        with Session() as session:
            pid = session.execute(text("SELECT pg_backend_pid()")).scalar_one()
            return revoke_sessions(session, clinic_id=clinic_id, user_id=user_id,
                                   actor=session.get(User, actor_id), reason="Synthetic concurrency test")

    try:
        with Session() as rotation:
            user = _lock_mfa_user(rotation, rotation.get(User, user_id))
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(admin_revoke)
                try:
                    deadline = time.monotonic() + 5
                    blocked = False
                    while time.monotonic() < deadline and not future.done():
                        with engine.connect() as observer:
                            if pid is not None:
                                blocked = observer.execute(text(
                                    "SELECT wait_event_type = 'Lock' AND query LIKE 'SELECT %' "
                                    "FROM pg_stat_activity WHERE pid=:pid"), {"pid": pid}).scalar() is True
                        if blocked:
                            break
                        time.sleep(0.01)
                    assert blocked, "Administrator revocation did not first wait on the user lock"
                    _, _, replacement = rotate_refresh_token(rotation, raw_token=raw)
                    replacement_id = replacement.id
                    assert future.result(timeout=5) == 1
                finally:
                    rotation.rollback()
        with Session() as check:
            assert check.get(RefreshToken, replacement_id).revoked_at is not None
            assert check.query(RefreshToken).filter(
                RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)).count() == 0
    finally:
        engine.dispose()
