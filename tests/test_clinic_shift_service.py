import pytest

import models
from services.clinic_shift_service import ShiftConflict, close_shift, open_shift, serialize_shift


def _clinic_actor(db_session):
    from core.provisioning_context import provisioning_channel
    from security import hash_password
    clinic = models.Clinic(name="Clinique Relève", is_active=True)
    db_session.add(clinic); db_session.commit()
    with provisioning_channel("test_fixture"):
        actor = models.User(email=f"shift-{clinic.id}@test.gn", hashed_password=hash_password("Secret12Pass!"), role="clinic_admin", clinic_id=clinic.id)
        db_session.add(actor); db_session.commit()
    return clinic, actor


def test_shift_requires_notes_for_incomplete_opening_and_only_one_open(db_session):
    clinic, actor = _clinic_actor(db_session)
    with pytest.raises(ShiftConflict):
        open_shift(db_session, clinic_id=clinic.id, actor_id=actor.id, printer_ready=False, offline_ready=True, offline_pending_count=0, notes=None)
    row = open_shift(db_session, clinic_id=clinic.id, actor_id=actor.id, printer_ready=False, offline_ready=True, offline_pending_count=0, notes="Imprimante de secours prête")
    assert serialize_shift(row)["opening_snapshot"]["printer_ready"] is False
    with pytest.raises(ShiftConflict):
        open_shift(db_session, clinic_id=clinic.id, actor_id=actor.id, printer_ready=True, offline_ready=True, offline_pending_count=0, notes=None)


def test_closing_preserves_unresolved_handoff(db_session):
    clinic, actor = _clinic_actor(db_session)
    row = open_shift(db_session, clinic_id=clinic.id, actor_id=actor.id, printer_ready=True, offline_ready=True, offline_pending_count=0, notes=None)
    db_session.add(models.ClinicCharge(clinic_id=clinic.id, patient_id=1, charge_type="consultation", source_type="appointment", source_id=999, description="Test", amount_gnf=1000, payment_status="pending"))
    # Patient FK is not enforced by the SQLite fixture; the pending charge is enough to prove handoff behavior.
    db_session.commit()
    with pytest.raises(ShiftConflict):
        close_shift(db_session, clinic_id=clinic.id, actor_id=actor.id, printer_ready=True, offline_pending_count=0, acknowledge_unresolved=False, notes=None)
    closed = close_shift(db_session, clinic_id=clinic.id, actor_id=actor.id, printer_ready=True, offline_pending_count=0, acknowledge_unresolved=True, notes="Facture transmise à la caisse de nuit")
    result = serialize_shift(closed)
    assert result["status"] == "closed"
    assert any(item["key"] == "cashier_pending_charges" for item in result["closing_snapshot"]["unresolved"])
    assert result["closing_notes"] == "Facture transmise à la caisse de nuit"
