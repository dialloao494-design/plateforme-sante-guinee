"""Heuristics to classify clinics for the platform owner directory."""

from __future__ import annotations

from typing import Iterable

DEMO_NAME_KEYWORDS = ("demo", "pilote", "pilot", "demonstration")
TEST_NAME_KEYWORDS = (
    "test",
    "e2e",
    "stress",
    "staging",
    "clinique alpha",
    "clinique beta",
    "alpha conakry",
    "beta conakry",
)


def is_staging_test_email(email: str) -> bool:
    e = (email or "").lower().strip()
    if not e:
        return False
    if e.endswith("@sante-gn.test"):
        return True
    if e.endswith("@pilot.local") or e.endswith("@clinic.test"):
        return True
    local = e.split("@")[0]
    if e.endswith("@example.com") and local in {"newpat", "o", "o2"}:
        return True
    if e.endswith("@patient.gn"):
        return True
    return False


def classify_clinic(
    *,
    name: str,
    is_active: bool,
    staff_emails: Iterable[str],
    patient_count: int = 0,
) -> str:
    """Return: production | demo | test | archived."""
    if not is_active:
        return "archived"

    if patient_count > 0:
        return "production"

    name_lower = (name or "").lower()
    if any(keyword in name_lower for keyword in DEMO_NAME_KEYWORDS):
        return "demo"
    if any(keyword in name_lower for keyword in TEST_NAME_KEYWORDS):
        return "test"

    emails = [e for e in staff_emails if e]
    if emails and all(is_staging_test_email(e) for e in emails):
        return "test"

    return "production"
