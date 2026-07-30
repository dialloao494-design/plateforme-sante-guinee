#!/usr/bin/env python3
"""Smoke checks for Security Wave 7 certification artifacts."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    failures: list[str] = []
    report = ROOT / "evidence" / "security" / "PRODUCTION_SECURITY_READINESS_REPORT.md"
    cert = ROOT / "evidence" / "security" / "WAVE7_CERTIFICATION.json"
    for path in (
        report,
        cert,
        ROOT / "docs" / "PRODUCTION_SECURITY_OPS_ATTESTATION.md",
        ROOT / "deploy" / "clinic-node" / "compose.yml",
        ROOT / "scripts" / "deploy" / "validate_security_wave7.py",
    ):
        if not path.is_file() and not path.exists():
            failures.append(f"missing:{path.relative_to(ROOT)}")

    if report.is_file():
        text = report.read_text(encoding="utf-8")
        if "GO FOR PRODUCTION SECURITY DEPLOYMENT" not in text:
            failures.append("report_missing_go_verdict")
        if "NO-GO" in text.split("## VERDICT", 1)[-1].split("## 1.", 1)[0] and "GO FOR" not in text:
            failures.append("report_verdict_conflict")

    if cert.is_file():
        data = json.loads(cert.read_text(encoding="utf-8"))
        if data.get("verdict") != "GO FOR PRODUCTION SECURITY DEPLOYMENT":
            failures.append(f"cert_verdict:{data.get('verdict')}")
        if data.get("go_blockers"):
            failures.append(f"cert_blockers:{data.get('go_blockers')}")
        if data.get("pentest", {}).get("critical_exploited"):
            failures.append("critical_exploited_remain")

    if failures:
        print("WAVE7 SMOKE FAIL:", "; ".join(failures))
        return 1
    print("WAVE7 SMOKE OK — GO FOR PRODUCTION SECURITY DEPLOYMENT")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
