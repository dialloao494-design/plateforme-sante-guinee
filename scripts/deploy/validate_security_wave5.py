#!/usr/bin/env python3
"""Static + functional smoke checks for Security Wave 5 (sync/DR/updates)."""

from __future__ import annotations

import gzip
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main() -> int:
    failures: list[str] = []
    os.environ.setdefault("ENVIRONMENT", "development")

    required = [
        ROOT / "core" / "sync_security.py",
        ROOT / "core" / "backup_security.py",
        ROOT / "core" / "update_security.py",
        ROOT / "services" / "recovery_security_service.py",
        ROOT / "docs" / "DISASTER_RECOVERY_SECURITY.md",
        ROOT / "scripts" / "security" / "encrypt_backup.py",
        ROOT / "scripts" / "security" / "apply_update.sh",
        ROOT / "tests" / "test_security_wave5_sync_dr.py",
    ]
    for path in required:
        if not path.is_file():
            failures.append(f"missing:{path.relative_to(ROOT)}")

    from cryptography.fernet import Fernet

    from core.backup_security import disaster_recovery_checklist, encrypt_backup_file
    from core.sync_security import ReplayGuard, build_signed_envelope, verify_signed_envelope
    from core.update_security import UpdateSecurityError, load_and_verify_package, write_signed_package
    from services.recovery_security_service import validate_recovery_scenarios

    secret = "wave5-smoke-sync-" + ("S" * 16)
    env = build_signed_envelope(
        secret=secret,
        event_id="smoke-1",
        clinic_id=1,
        entity_type="patient",
        operation="upsert",
        payload={"ok": True},
    ).to_dict()
    ok, reason = verify_signed_envelope(env, secret=secret)
    if not ok:
        failures.append(f"envelope:{reason}")
    guard = ReplayGuard()
    if not guard.consume_envelope(env)[0]:
        failures.append("replay_first")
    if guard.consume_envelope(env)[0]:
        failures.append("replay_not_blocked")

    key = Fernet.generate_key().decode()
    os.environ["BACKUP_ENCRYPTION_KEY"] = key
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        plain = tmp_path / "dump.sql.gz"
        with gzip.open(plain, "wb", compresslevel=1) as gz:
            gz.write(
                b"--\n-- PostgreSQL database dump\nCREATE TABLE t(id int);\n"
                + (b"-- pad for min size\n" * 400)
                + os.urandom(256)
            )
        enc = encrypt_backup_file(plain, tmp_path / "dump.sql.gz.enc", key=key)
        report = validate_recovery_scenarios(
            plain_backup=plain,
            encrypted_backup=enc.path,
            require_encryption=True,
            key=key,
        )
        if not report.get("ok"):
            failures.append(f"recovery_scenarios:{report}")

        update_secret = "wave5-smoke-update-" + ("U" * 16)
        os.environ["CLINIC_NODE_UPDATE_SECRET"] = update_secret
        os.environ["ENVIRONMENT"] = "clinic-node"
        pkg = tmp_path / "pkg"
        write_signed_package(pkg, {"version": "0.0.1-smoke", "backup_required": True}, secret=update_secret)
        loaded = load_and_verify_package(pkg, secret=update_secret)
        if loaded.version != "0.0.1-smoke":
            failures.append("update_version")
        (pkg / "manifest.sig").write_text("00" * 32 + "\n", encoding="utf-8")
        try:
            load_and_verify_package(pkg, secret=update_secret)
            failures.append("bad_sig_accepted")
        except UpdateSecurityError:
            pass

    if len(disaster_recovery_checklist()) < 8:
        failures.append("dr_checklist_short")

    proc = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "tests/test_security_wave5_sync_dr.py",
        ],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "ENVIRONMENT": "development",
            "ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
        },
    )
    if proc.returncode != 0:
        failures.append(f"pytest:\n{proc.stdout}\n{proc.stderr}")

    if failures:
        print("WAVE5 SMOKE FAIL:", "; ".join(failures))
        return 1
    print("WAVE5 SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
