#!/usr/bin/env python3
"""Create or repair a test user in the active database."""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

load_dotenv()

from database import DATABASE_URL, SessionLocal
from models.user import User
from security import hash_password, verify_password


DEFAULT_EMAIL = "test123@gmail.com"
DEFAULT_PASSWORD = "123456"
DEFAULT_ROLE = "patient"


def create_test_user(email: str = DEFAULT_EMAIL, password: str = DEFAULT_PASSWORD, role: str = DEFAULT_ROLE) -> None:
    """Create the requested test user or update the password if it already exists."""
    if not DATABASE_URL:
        raise RuntimeError("DATABASE_URL is required")

    print("Using database:", DATABASE_URL)
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()
        if user is None:
            user = User(
                email=email,
                hashed_password=hash_password(password),
                role=role,
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            status = "created"
        else:
            password_ok = False
            try:
                password_ok = verify_password(password, user.hashed_password)
            except Exception:
                password_ok = False

            changed = False
            if not password_ok:
                user.hashed_password = hash_password(password)
                changed = True
            if user.role != role:
                user.role = role
                changed = True
            if changed:
                db.commit()
                db.refresh(user)
            status = "existing" if not changed else "updated"

        print("✅ Test user ready")
        print(f"   Status: {status}")
        print(f"   Email: {user.email}")
        print(f"   Role: {user.role}")
        print(f"   ID: {user.id}")
    except Exception as exc:
        db.rollback()
        print(f"❌ Error creating test user: {exc}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    email = os.getenv("TEST_USER_EMAIL") or (sys.argv[1] if len(sys.argv) > 1 else DEFAULT_EMAIL)
    password = os.getenv("TEST_USER_PASSWORD") or (sys.argv[2] if len(sys.argv) > 2 else DEFAULT_PASSWORD)
    role = os.getenv("TEST_USER_ROLE") or (sys.argv[3] if len(sys.argv) > 3 else DEFAULT_ROLE)
    create_test_user(email=email, password=password, role=role)