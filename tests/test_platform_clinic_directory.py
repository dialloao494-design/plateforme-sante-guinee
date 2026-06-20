"""Platform owner clinic directory API."""

from __future__ import annotations

import pytest

from core.provisioning_context import provisioning_channel
from models.clinic import Clinic
from models.patient import Patient
from services.user_provisioning import create_clinic_admin_user, create_staff_user


class TestPlatformClinicDirectory:
    def test_summary_defaults_to_production_only(self, client, db_session, admin_headers):
        with provisioning_channel("test"):
            koloma = Clinic(name="Centre de Santé Koloma", city="Conakry", is_active=True)
            demo = Clinic(name="Clinique Pilote Demo", city="Conakry", is_active=True)
            test_clinic = Clinic(name="Clinique Alpha Conakry", city="Conakry", is_active=True)
            db_session.add_all([koloma, demo, test_clinic])
            db_session.flush()

            create_clinic_admin_user(
                db_session,
                email="koloma.admin@real-clinic.gn",
                password="KolomaPass1!",
                clinic_id=koloma.id,
                channel="admin_api",
            )
            create_staff_user(
                db_session,
                email="staff@pilot.local",
                password="StaffPass1!",
                role="receptionist",
                clinic_id=demo.id,
                channel="test_fixture",
            )
            create_staff_user(
                db_session,
                email="alpha@test.sante-gn.test",
                password="StaffPass1!",
                role="receptionist",
                clinic_id=test_clinic.id,
                channel="test_fixture",
            )
            db_session.add(
                Patient(
                    clinic_id=koloma.id,
                    first_name="A",
                    last_name="Patient",
                    age=30,
                    gender="other",
                )
            )
            db_session.commit()

        r = client.get("/platform/summary", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total_clinics"] == 1
        assert data["total_patients"] == 1

    def test_directory_search_by_name_and_admin(self, client, db_session, admin_headers):
        with provisioning_channel("test"):
            aasma = Clinic(name="Polyclinique Aasma", city="Conakry", is_active=True)
            db_session.add(aasma)
            db_session.flush()
            create_clinic_admin_user(
                db_session,
                email="contactpolycliniqueaasma@gmail.com",
                password="AasmaPass1!",
                clinic_id=aasma.id,
                channel="admin_api",
            )
            db_session.commit()

        by_name = client.get(
            "/platform/clinics/directory",
            params={"category": "production", "search": "Aasma"},
            headers=admin_headers,
        )
        assert by_name.status_code == 200
        assert len(by_name.json()) == 1
        assert by_name.json()[0]["name"] == "Polyclinique Aasma"

        by_admin = client.get(
            "/platform/clinics/directory",
            params={"category": "production", "search": "contactpolycliniqueaasma@gmail.com"},
            headers=admin_headers,
        )
        assert by_admin.status_code == 200
        assert len(by_admin.json()) == 1

    def test_clinic_detail_and_staff_scoped(self, client, db_session, admin_headers):
        with provisioning_channel("test"):
            k = Clinic(name="Centre de Santé Koloma", city="Conakry", is_active=True)
            a = Clinic(name="Polyclinique Aasma", city="Conakry", is_active=True)
            db_session.add_all([k, a])
            db_session.flush()
            create_clinic_admin_user(
                db_session,
                email="koloma.admin@real.gn",
                password="KolomaPass1!",
                clinic_id=k.id,
                channel="admin_api",
            )
            create_staff_user(
                db_session,
                email="aasma.reception@real.gn",
                password="StaffPass1!",
                role="receptionist",
                clinic_id=a.id,
                channel="test_fixture",
            )
            db_session.commit()
            koloma_id = k.id
            aasma_id = a.id

        detail = client.get(f"/platform/clinics/{koloma_id}/detail", headers=admin_headers)
        assert detail.status_code == 200
        assert detail.json()["admin_email"] == "koloma.admin@real.gn"

        koloma_staff = client.get(f"/platform/clinics/{koloma_id}/staff", headers=admin_headers)
        assert koloma_staff.status_code == 200
        emails = {row["email"] for row in koloma_staff.json()}
        assert "koloma.admin@real.gn" in emails
        assert "aasma.reception@real.gn" not in emails

        aasma_staff = client.get(f"/platform/clinics/{aasma_id}/staff", headers=admin_headers)
        assert len(aasma_staff.json()) == 1
        assert aasma_staff.json()[0]["email"] == "aasma.reception@real.gn"

    def test_reset_staff_password(self, client, db_session, admin_headers):
        nurse_email = "nurse@koloma.gn"
        with provisioning_channel("test"):
            clinic = Clinic(name="Centre de Santé Koloma", city="Conakry", is_active=True)
            db_session.add(clinic)
            db_session.flush()
            provisioned = create_staff_user(
                db_session,
                email=nurse_email,
                password="OldPass123!",
                role="nurse",
                clinic_id=clinic.id,
                channel="test_fixture",
            )
            db_session.commit()
            clinic_id = clinic.id
            nurse_id = provisioned.user.id

        r = client.post(
            f"/platform/clinics/{clinic_id}/staff/{nurse_id}/reset-password",
            json={"new_password": "NewSecure1!"},
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text

        login_ok = client.post(
            "/auth/login-json",
            json={"email": nurse_email, "password": "NewSecure1!"},
        )
        assert login_ok.status_code == 200

    def test_test_accounts_hidden_from_production_filter(self, client, db_session, admin_headers):
        with provisioning_channel("test"):
            clinic = Clinic(name="Stress Test Clinic", city="Conakry", is_active=True)
            db_session.add(clinic)
            db_session.flush()
            create_staff_user(
                db_session,
                email="stress@sante-gn.test",
                password="StaffPass1!",
                role="receptionist",
                clinic_id=clinic.id,
                channel="test_fixture",
            )
            db_session.commit()

        prod = client.get(
            "/platform/clinics/directory",
            params={"category": "production"},
            headers=admin_headers,
        )
        assert all(c["category"] != "test" for c in prod.json())

        test_only = client.get(
            "/platform/clinics/directory",
            params={"category": "test"},
            headers=admin_headers,
        )
        assert len(test_only.json()) >= 1

    def test_clinic_with_patients_is_production(self, client, db_session, admin_headers):
        with provisioning_channel("test"):
            clinic = Clinic(name="Stress Test Clinic", city="Conakry", is_active=True)
            db_session.add(clinic)
            db_session.flush()
            create_staff_user(
                db_session,
                email="stress-patients-prod@sante-gn.test",
                password="StaffPass1!",
                role="receptionist",
                clinic_id=clinic.id,
                channel="test_fixture",
            )
            db_session.add(
                Patient(
                    clinic_id=clinic.id,
                    first_name="Real",
                    last_name="Patient",
                    age=25,
                    gender="other",
                )
            )
            db_session.commit()
            clinic_id = clinic.id

        detail = client.get(f"/platform/clinics/{clinic_id}/detail", headers=admin_headers)
        assert detail.status_code == 200
        assert detail.json()["category"] == "production"
