#!/usr/bin/env python3
"""Run all production browser E2E workflows (reception/lab/pharmacy + nurse)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = [
    ROOT / "scripts" / "deploy" / "aasma_browser_e2e.py",
    ROOT / "scripts" / "deploy" / "aasma_nurse_workflow_e2e.py",
]


def main() -> int:
    failed = []
    for script in SCRIPTS:
        print(f"\n========== {script.name} ==========\n")
        rc = subprocess.call([sys.executable, str(script)])
        if rc != 0:
            failed.append(script.name)
    if failed:
        print(f"\nFAILED: {', '.join(failed)}", file=sys.stderr)
        return 1
    print("\nAll production browser E2E workflows passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
