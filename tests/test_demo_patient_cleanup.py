from services.demo_patient_cleanup import is_test_patient_name


def test_matches_e2e_and_dashboard_names():
    assert is_test_patient_name("Clinic", "E2E009161")
    assert is_test_patient_name("Aissatou", "Dashboard231409")
    assert is_test_patient_name("Harden", "E2EAB12CD34")
    assert is_test_patient_name("LabDbg", "E2E24ccd2")
    assert is_test_patient_name("Recep348151", "Test348151")


def test_keeps_real_patient_names():
    assert not is_test_patient_name("Fatoumata", "Camara")
    assert not is_test_patient_name("Mamadou", "Diallo")
    assert not is_test_patient_name("Aissatou", "Bah")
