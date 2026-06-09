#!/usr/bin/env python3
"""Recalculate meeting_link for existing teleconsultation appointments."""
from __future__ import annotations

import hashlib
import os
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _room_name(appointment_id: int) -> str:
    salt = (os.getenv("SECRET_KEY") or "dev")[:16]
    digest = hashlib.sha256(f"{salt}:appt:{appointment_id}".encode()).hexdigest()[:12]
    return f"sante-gn-{appointment_id}-{digest}"


def _meeting_link(appointment_id: int) -> str:
    domain = (os.getenv("JITSI_DOMAIN") or os.getenv("JITSI_SELF_HOSTED_DOMAIN", "127.0.0.1:8443")).strip().replace("https://", "").rstrip("/")
    return f"https://{domain}/{_room_name(appointment_id)}"


def main() -> int:
    db_path = ROOT / "sante.db"
    if not db_path.exists():
        print(f"No database at {db_path}")
        return 1

    conn = sqlite3.connect(db_path)
    rows = conn.execute(
        "SELECT id, meeting_link FROM rendezvous WHERE consultation_type = 'teleconsultation'"
    ).fetchall()

    updated = 0
    for appt_id, old_link in rows:
        new_link = _meeting_link(appt_id)
        if old_link != new_link:
            conn.execute("UPDATE rendezvous SET meeting_link = ? WHERE id = ?", (new_link, appt_id))
            print(f"  #{appt_id}: {old_link} -> {new_link}")
            updated += 1

    conn.commit()
    conn.close()
    print(f"Done. Updated {updated}/{len(rows)} teleconsultation appointment(s).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
