#!/usr/bin/env python3
"""Audit AASMA lab catalog completeness against paper forms (no pricing)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from data.aasma_lab_catalog import AASMA_LAB_CATALOG, AASMA_EXAM_COUNT

API = "https://web-production-ad6a36.up.railway.app"
OUT = ROOT / "docs" / "AASMA_CATALOG_COMPLETENESS.json"

# Original AASMA paper form exam names (pre-tariff merge)
ORIGINAL_FORMS = subprocess.check_output(
    ["git", "show", "d9f6e7f:data/aasma_lab_catalog.py"],
    cwd=ROOT,
    text=True,
    encoding="utf-8",
    errors="replace",
)

FORM_NAMES: list[str] = []
for line in ORIGINAL_FORMS.splitlines():
    if '("' in line and '", "' in line and line.strip().startswith("("):
        parts = line.split('", "', 1)
        if len(parts) == 2:
            name = parts[1].split('"')[0]
            FORM_NAMES.append(name)

HPYLORI_ALIASES = {
    "h. pylori dans le sang",
    "h.pylori dans le sang",
    "h. pylori dans les selles",
    "h.pylori dans les selles",
}


def norm(name: str) -> str:
    return " ".join(name.lower().replace(".", ". ").split())


def match_form_name(form_name: str, catalog_names: set[str]) -> bool:
    n = norm(form_name)
    if n in catalog_names:
        return True
    if n in HPYLORI_ALIASES and any(a in catalog_names for a in HPYLORI_ALIASES):
        return True
    stem = n.split("(")[0].strip()
    return any(stem in c or c in stem for c in catalog_names if len(stem) >= 4)


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
    catalog_names = {norm(t["name"]) for t in tests}
    by_category = {}
    for t in tests:
        by_category.setdefault(t["category_label"], []).append(t["name"])

    missing = [name for name in FORM_NAMES if not match_form_name(name, catalog_names)]
    hpylori = [
        t for t in tests if "pylori" in t["name"].lower()
    ]

    report = {
        "expected_exams": AASMA_EXAM_COUNT,
        "production_exams": len(tests),
        "form_reference_count": len(FORM_NAMES),
        "missing_from_forms": missing,
        "h_pylori_entries": hpylori,
        "categories": {k: len(v) for k, v in by_category.items()},
        "ok": not missing and len(hpylori) >= 2,
    }
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
