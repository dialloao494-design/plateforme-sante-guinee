#!/usr/bin/env python3
"""
Provision the production Platform Owner account (one-time, real credentials only).

Usage:
  PLATFORM_OWNER_EMAIL=you@company.com PLATFORM_OWNER_PASSWORD='YourSecure1!' \\
    python scripts/deploy/provision_platform_owner.py

Never use demo, seed, or test emails with this script.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from database import SessionLocal
from services.user_provisioning import (
    EmailAlreadyRegisteredError,
    UserProvisioningError,
    create_platform_owner_user,
)
import models


def main() -> int:
    email = (os.environ.get("PLATFORM_OWNER_EMAIL") or "").strip().lower()
    password = os.environ.get("PLATFORM_OWNER_PASSWORD") or ""

    if not email or not password:
        print("ERROR: Set PLATFORM_OWNER_EMAIL and PLATFORM_OWNER_PASSWORD", file=sys.stderr)
        return 1

    if email.endswith("@sante-gn.test") or "demo" in email or "test" in email.split("@")[0]:
        print("ERROR: Refusing demo/test email for production platform owner.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        existing = db.query(models.User).filter(models.User.email == email).first()
        if existing:
            if existing.role == "platform_owner":
                print(f"Platform owner already exists: {existing.email} (id={existing.id})")
                return 0
            print(
                f"ERROR: Account already exists with role={existing.role}; "
                "refusing an implicit privilege escalation.",
                file=sys.stderr,
            )
            return 1

        provisioned = create_platform_owner_user(
            db,
            email=email,
            password=password,
            channel="platform_owner_bootstrap",
        )
        provisioned.user.must_change_password = True
        db.commit()
        print(f"Platform owner created: {provisioned.user.email} (id={provisioned.user.id})")
        return 0
    except (EmailAlreadyRegisteredError, UserProvisioningError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    sys.exit(main())
