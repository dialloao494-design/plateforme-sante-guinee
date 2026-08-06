import models
from services.demo_patient_cleanup import is_test_patient_name, list_demo_patients


def test_matches_e2e_and_dashboard_names():
    assert is_test_patient_name("Clinic", "E2E009161")
    assert is_test_patient_name("Aissatou", "Dashboard231409")
    assert is_test_patient_name("Harden", "E2EAB12CD34")
    assert is_test_patient_name("LabDbg", "E2E24ccd2")
    assert is_test_patient_name("Recep348151", "Test348151")
    assert is_test_patient_name("Alpha", "DeployIsoaa018f30")
    assert is_test_patient_name("Amadou", "Bah-61b233")
    assert is_test_patient_name("Proof404192", "User404192")
    assert is_test_patient_name("Patient", "Audit75384d")
    assert is_test_patient_name("E2ECleanup33", "E2ECleanup33")
    assert is_test_patient_name("C", "Mf00a43")


def test_keeps_real_patient_names():
    assert not is_test_patient_name("Fatoumata", "Camara")
    assert not is_test_patient_name("Mamadou", "Diallo")
    assert not is_test_patient_name("Aissatou", "Bah")
    assert not is_test_patient_name("Oumou Salamata", "BALDE")
    assert not is_test_patient_name("Cathérine", "KAMANO")


def test_list_demo_patients_includes_archived(db_session):
    """Archived synthetic patients must still be purgeable."""
    clinic = models.Clinic(name="Cleanup Test Clinic", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)

    active = models.Patient(
        clinic_id=clinic.id, first_name="E2E", last_name="E2ECleanupActive", age=30, gender="f"
    )
    archived = models.Patient(
        clinic_id=clinic.id, first_name="E2E", last_name="E2ECleanupArchived", age=30, gender="m"
    )
    archived.is_archived = True
    db_session.add_all([active, archived])
    db_session.commit()

    matched = list_demo_patients(db_session, clinic.id)
    ids = {p.id for p in matched}
    assert active.id in ids
    assert archived.id in ids
