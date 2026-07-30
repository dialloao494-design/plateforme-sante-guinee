#!/usr/bin/env python3
"""Verify clinic logo appears in generated PDF receipts."""
from __future__ import annotations
import os


import httpx

BACKEND = "https://web-production-ad6a36.up.railway.app"
EMAIL, PWD = "baldoumar14@gmail.com", os.environ["AASMA_RECEPTION_PASSWORD"]


def login() -> str:
    r = httpx.post(f"{BACKEND}/auth/login-json", json={"email": EMAIL, "password": PWD}, timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]


def main() -> None:
    tok = login()
    h = {"Authorization": f"Bearer {tok}"}
    inv = httpx.get(f"{BACKEND}/clinical/reception/his/invoices", headers=h, timeout=60)
    inv.raise_for_status()
    rows = inv.json()
    if not rows:
        print("SKIP: no invoices to test")
        return
    pdf = httpx.get(
        f"{BACKEND}/clinical/reception/his/invoices/{rows[0]['id']}/receipt",
        headers=h,
        timeout=60,
    )
    pdf.raise_for_status()
    data = pdf.content
    checks = [
        ("pdf_header", data[:4] == b"%PDF"),
        ("jpeg_logo", b"DCTDecode" in data),
        ("clinic_name", b"POLYCLINIQUE" in data),
    ]
    for name, ok in checks:
        print(name, "PASS" if ok else "FAIL")
    if not all(ok for _, ok in checks):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
