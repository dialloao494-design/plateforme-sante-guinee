"""Pilot seed credentials must satisfy the production password policy."""

from core.password_policy import validate_password
from services.clinic_pilot_seed import PILOT_STAFF


def test_all_pilot_staff_passwords_meet_policy():
    for spec in PILOT_STAFF:
        assert validate_password(spec["password"]) is True, spec["email"]


def test_pev_pilot_password_is_long_enough():
    pev = next(s for s in PILOT_STAFF if s["email"] == "pev@pilot.local")
    assert len(pev["password"]) >= 12
    assert pev["password"] == "PevAgentPilot1!"
