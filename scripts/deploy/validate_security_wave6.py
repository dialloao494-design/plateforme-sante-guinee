#!/usr/bin/env python3
"""Smoke validator for Security Wave 6 penetration testing artifacts."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def main() -> int:
    failures: list[str] = []
    required = [
        ROOT / "docs" / "PENETRATION_TESTING_PLAN.md",
        ROOT / "scripts" / "security" / "run_penetration_tests.py",
        ROOT / "tests" / "test_security_wave6_pentest.py",
        ROOT / "evidence" / "security" / "WAVE6_PENETRATION_TESTING_REPORT.md",
        ROOT / "evidence" / "security" / "WAVE6_REMEDIATION_REPORT.md",
        ROOT / "evidence" / "security" / "WAVE6_RESIDUAL_RISKS.md",
    ]
    for path in required:
        if not path.is_file():
            failures.append(f"missing:{path.relative_to(ROOT)}")

    env = {
        **os.environ,
        "ENVIRONMENT": "development",
        "ALLOWED_HOSTS": "localhost,127.0.0.1,testserver",
        "DATABASE_URL": "sqlite://",
        "SECRET_KEY": os.environ.get("SECRET_KEY", "wave6-pentest-secret-key-32chars-min!!"),
        "PASSWORD_MIN_LENGTH": "12",
        "LOGIN_MAX_FAILURES": "5",
        "BCRYPT_ROUNDS": "4",
        "RATE_LIMIT_LOGIN": "10000/minute",
        "RATE_LIMIT_DEFAULT": "10000/minute",
    }
    proc = subprocess.run(
        [sys.executable, "-B", str(ROOT / "scripts" / "security" / "run_penetration_tests.py")],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        env=env,
    )
    if proc.returncode != 0:
        failures.append(f"harness_exit={proc.returncode}\n{proc.stdout}\n{proc.stderr}")

    results = ROOT / "evidence" / "security" / "wave6" / "WAVE6_ATTACK_RESULTS.json"
    if results.is_file():
        data = json.loads(results.read_text(encoding="utf-8"))
        if data.get("critical_exploited"):
            failures.append(f"critical_exploited:{data['critical_exploited']}")
        if data.get("results", {}).get("EXPLOITED", 1) != 0:
            failures.append(f"exploited_count:{data.get('results')}")
        if data.get("attack_count_executed") != 38:
            failures.append(f"attack_count:{data.get('attack_count_executed')}")
    else:
        failures.append("missing_attack_results_json")

    if failures:
        print("WAVE6 SMOKE FAIL:", "; ".join(failures))
        return 1
    print("WAVE6 SMOKE OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
