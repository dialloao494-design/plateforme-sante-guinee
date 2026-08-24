import models
from core.provisioning_context import provisioning_channel

from services.clinic_onboarding_service import readiness, update_onboarding


def test_readiness_is_derived_from_real_clinic_state(db_session):
    clinic = models.Clinic(name="Clinique Test", address="Conakry", city="Conakry", phone="620000000")
    db_session.add(clinic)
    db_session.commit()
    initial = readiness(db_session, clinic)
    assert initial["is_operational"] is False
    assert {item["key"] for item in initial["checklist"] if not item["complete"]} >= {"staff", "printing", "offline", "journey"}
    with provisioning_channel("test_fixture"):
        db_session.add(models.User(email=f"onboarding-{clinic.id}@test.local", hashed_password="unused", role="receptionist", clinic_id=clinic.id, is_active=True))
        db_session.commit()
    result = update_onboarding(db_session, clinic, {
        "enabled_modules": ["reception", "billing"], "payment_methods": ["cash"],
        "printing_tested": True, "offline_workstation_tested": True, "test_journey_completed": True,
    })
    assert result["is_operational"] is True
    assert result["percent"] == 100
    assert clinic.onboarding_completed_at is not None


def test_hospitalization_requires_a_real_bed(db_session):
    clinic = models.Clinic(name="Clinique Lits", address="Ratoma", city="Conakry", phone="621000000")
    db_session.add(clinic)
    db_session.commit()
    result = update_onboarding(db_session, clinic, {"enabled_modules": ["hospitalization"]})
    assert next(item for item in result["checklist"] if item["key"] == "capacity")["complete"] is False
    room = models.HospitalRoom(clinic_id=clinic.id, ward_name="Médecine", room_number="101", capacity=1, status="active")
    db_session.add(room)
    db_session.commit()
    db_session.add(models.HospitalBed(room_id=room.id, bed_number="A", status="available"))
    db_session.commit()
    capacity = next(item for item in readiness(db_session, clinic)["checklist"] if item["key"] == "capacity")
    assert capacity["complete"] is True
    assert "1 lit" in capacity["detail"]


def test_onboarding_rejects_unknown_modules(db_session):
    clinic = models.Clinic(name="Clinique Validation")
    db_session.add(clinic)
    db_session.commit()
    try:
        update_onboarding(db_session, clinic, {"enabled_modules": ["unknown"]})
    except ValueError as exc:
        assert "Modules inconnus" in str(exc)
    else:
        raise AssertionError("Unknown module should be rejected")
