#!/usr/bin/env python3
"""Sync all pilot doctors' availability on remote demo API (08:00–20:00, Mon–Sun)."""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.pilot_seed import PILOT_DOCTOR_PASSWORD, PILOT_DOCTORS

BASE = os.getenv("API_BASE", "http://158.220.83.42/api").rstrip("/")
START = "08:00:00"
END = "20:00:00"


def req(method: str, path: str, token: str | None = None, body: dict | None = None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=30) as resp:
        raw = resp.read().decode()
        return json.loads(raw) if raw else {}


def sync_doctor(token: str, doctor_id: int) -> None:
    slots = req("GET", f"/doctors/{doctor_id}/availability", token=token)
    by_day = {s["day_of_week"]: s for s in slots if s.get("is_active", True)}
    for day in range(7):
        if day in by_day:
            slot = by_day[day]
            req(
                "PUT",
                f"/doctors/{doctor_id}/availability/{slot['id']}",
                token=token,
                body={"start_time": START, "end_time": END, "is_active": True},
            )
        else:
            try:
                req(
                    "POST",
                    f"/doctors/{doctor_id}/availability",
                    token=token,
                    body={
                        "doctor_id": doctor_id,
                        "day_of_week": day,
                        "start_time": START,
                        "end_time": END,
                    },
                )
            except urllib.error.HTTPError:
                pass


def main() -> int:
    for row in PILOT_DOCTORS:
        email = row["email"]
        login = req(
            "POST",
            "/auth/login-json",
            body={"email": email, "password": PILOT_DOCTOR_PASSWORD},
        )
        token = login["access_token"]
        me = req("GET", "/auth/me", token=token)
        doc_id = int(me["doctor_id"])
        print(f"Sync {email} (doctor_id={doc_id})")
        sync_doctor(token, doc_id)
    print("Done — all pilot doctors 08:00-20:00 Mon-Sun")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
