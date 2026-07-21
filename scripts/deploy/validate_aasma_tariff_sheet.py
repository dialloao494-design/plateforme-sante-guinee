#!/usr/bin/env python3
"""Validate production catalog against the 4 AASMA tariff sheet photos."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data.aasma_lab_catalog import _AASMA_TARIFF_LINES

API = "https://web-production-ad6a36.up.railway.app"
FRONTEND = "https://plateforme-sante-guinee.vercel.app"
OUT = ROOT / "docs" / "AASMA_TARIFF_SHEET_PROOF.json"


def main() -> int:
    login = requests.post(
        f"{API}/auth/login-json",
        json={"email": "mamadoudianbarry06@gmail.com", "password": "AasmaLab1!"},
        timeout=60,
    )
    login.raise_for_status()
    token = login.json()["access_token"]
    cat = requests.get(
        f"{API}/clinical/lab/catalog",
        headers={"Authorization": f"Bearer {token}"},
        timeout=60,
    )
    cat.raise_for_status()
    tests = cat.json().get("tests", [])
    by_name = {}
    for t in tests:
        by_name.setdefault(t["name"], []).append(t)

    mismatches = []
    missing = []
    for i, (category, name, price) in enumerate(_AASMA_TARIFF_LINES):
        rows = by_name.get(name)
        if not rows:
            missing.append({"index": i, "name": name, "price": price, "category": category})
            continue
        row = rows[0]
        if row.get("price_gnf") != price:
            mismatches.append(
                {
                    "index": i,
                    "name": name,
                    "expected": price,
                    "actual": row.get("price_gnf"),
                }
            )
        if row.get("category_label") != {
            "HEMATOLOGIE": "Hématologie",
            "HEMOSTASE": "Hémostase",
            "BIOCHIMIE": "Biochimie",
            "IMMUNO-SEROLOGIE": "Immuno-Sérologie",
            "BACTERIOLOGIE": "Bactériologie",
            "PARASITOLOGIE": "Parasitologie",
            "HORMONES": "Hormones",
            "REPRODUCTION / FERTILITE": "Reproduction/Fertilité",
            "MARQUEURS CANCEREUX": "Marqueurs Cancéreux",
            "AUTRES EXAMENS": "Autres examens",
        }.get(category):
            mismatches.append(
                {
                    "index": i,
                    "name": name,
                    "issue": "category",
                    "expected": category,
                    "actual": row.get("category_label"),
                }
            )

    report = {
        "tariff_lines": len(_AASMA_TARIFF_LINES),
        "production_tests": len(tests),
        "missing": missing,
        "mismatches": mismatches,
        "ok": not missing and not mismatches,
        "frontend": FRONTEND,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
