"""Red Team round-2 regressions — clinical IDOR / billing privilege bugs."""

from __future__ import annotations

from datetime import datetime, timedelta

import models
import pytest
from core.provisioning_context import provisioning_channel
from security import create_access_token, hash_password
from services.lab_clinical_service import LabClinicalService
from services.nurse_assessment_service import NurseAssessmentService
from services.pharmacy_clinical_service import PharmacyClinicalService


def _auth(user) -> dict[str, str]:
    token = create_access_token(
        {
            "sub": user.email,
            "user_id": user.id,
            "user_role": user.role,
            "role": user.role,
            "tv": int(getattr(user, "token_version", 0) or 0),
        }
    )
    return {"Authorization": f"Bearer {token}"}


def _clinic(db, name: str) -> models.Clinic:
    c = models.Clinic(name=name, city="Conakry", is_active=True)
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _user(db, *, email: str, role: str, clinic_id=None, password: str = "StrongPass12!"):
    with provisioning_channel("test_fixture"):
        u = models.User(
            email=email,
            hashed_password=hash_password(password),
            role=role,
            clinic_id=clinic_id,
            is_active=True,
            token_version=0,
        )
        db.add(u)
        db.commit()
        db.refresh(u)
    return u


def _doctor(db, *, clinic_id: int, email: str) -> models.Doctor:
    u = _user(db, email=email, role="doctor", clinic_id=clinic_id)
    d = models.Doctor(
        user_id=u.id,
        first_name="Doc",
        last_name="X",
        specialty="gp",
        city="Conakry",
        phone="620000000",
        clinic_id=clinic_id,
    )
    db.add(d)
    db.commit()
    db.refresh(d)
    return d


def _patient(db, *, clinic_id: int, name: str = "Pat") -> models.Patient:
    p = models.Patient(
        first_name=name,
        last_name="Test",
        age=30,
        gender="f",
        clinic_id=clinic_id,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


def test_rt2_nurse_cannot_sync_foreign_consultation(db_session):
    c1 = _clinic(db_session, "NA-C1")
    c2 = _clinic(db_session, "NA-C2")
    nurse = _user(db_session, email="nurse.na@test.gn", role="nurse", clinic_id=c1.id)
    p1 = _patient(db_session, clinic_id=c1.id, name="Local")
    p2 = _patient(db_session, clinic_id=c2.id, name="Foreign")
    doc2 = _doctor(db_session, clinic_id=c2.id, email="doc.na2@test.gn")
    appt = models.RendezVous(
        patient_id=p2.id,
        doctor_id=doc2.id,
        clinic_id=c2.id,
        date=datetime.utcnow() + timedelta(hours=1),
        duration_minutes=30,
        status="confirmed",
    )
    db_session.add(appt)
    db_session.commit()
    consult = models.ClinicalConsultation(
        clinic_id=c2.id,
        appointment_id=appt.id,
        patient_id=p2.id,
        doctor_id=doc2.id,
        status="in_progress",
        chief_complaint="ORIGINAL",
    )
    db_session.add(consult)
    db_session.commit()

    import schemas.nurse_assessment as na_schemas

    payload = na_schemas.NurseAssessmentCreate(
        patient_id=p1.id,
        consultation_id=consult.id,
        reason_for_consultation="HIJACKED COMPLAINT",
    )
    with pytest.raises(Exception):
        NurseAssessmentService.save_assessment(
            db_session, clinic_id=c1.id, payload=payload, actor=nurse
        )
    db_session.refresh(consult)
    assert consult.chief_complaint == "ORIGINAL"


def test_rt2_lab_default_doctor_no_global_fallback(db_session):
    c1 = _clinic(db_session, "Lab-C1")
    c2 = _clinic(db_session, "Lab-C2")
    _doctor(db_session, clinic_id=c2.id, email="only.other@test.gn")
    with pytest.raises(Exception):
        LabClinicalService._default_doctor(db_session, c1.id)


def test_rt2_pharmacy_default_doctor_no_global_fallback(db_session):
    c1 = _clinic(db_session, "Pharm-C1")
    c2 = _clinic(db_session, "Pharm-C2")
    _doctor(db_session, clinic_id=c2.id, email="only.other.ph@test.gn")
    with pytest.raises(Exception):
        PharmacyClinicalService._default_doctor(db_session, c1.id)


def test_rt2_lab_tech_cannot_mark_walkin_paid(client, db_session):
    from schemas.clinical import WalkInLabRequestCreate, WalkInLabTestItem

    c1 = _clinic(db_session, "LabPay-C1")
    tech = _user(db_session, email="lab.tech@test.gn", role="lab_technician", clinic_id=c1.id)
    _doctor(db_session, clinic_id=c1.id, email="lab.doc@test.gn")
    patient = _patient(db_session, clinic_id=c1.id, name="LabPat")
    payload = WalkInLabRequestCreate(
        patient_id=patient.id,
        tests=[WalkInLabTestItem(test_code="NFS", test_name="NFS", price_gnf=1)],
        payment_status="paid",
    )
    orders = LabClinicalService.create_walk_in_orders(
        db_session, clinic_id=c1.id, payload=payload, actor=tech
    )
    assert orders
    charge = (
        db_session.query(models.ClinicCharge)
        .filter(
            models.ClinicCharge.source_type == "lab_order",
            models.ClinicCharge.source_id == orders[0].id,
        )
        .first()
    )
    assert charge is not None
    assert charge.payment_status != "paid"
    assert charge.amount_gnf != 1  # client-supplied price ignored for lab tech


def test_rt2_clinic_admin_cannot_claim_unbound_doctor(client, db_session):
    c1 = _clinic(db_session, "Claim-C1")
    admin = _user(db_session, email="claim.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    unbound_user = _user(db_session, email="unbound.doc@test.gn", role="doctor", clinic_id=None)
    doctor = models.Doctor(
        user_id=unbound_user.id,
        first_name="Free",
        last_name="Agent",
        specialty="gp",
        city="Conakry",
        phone="621111111",
        clinic_id=None,
    )
    db_session.add(doctor)
    db_session.commit()
    r = client.patch(
        f"/clinical/doctors/{doctor.id}/clinic/{c1.id}",
        headers=_auth(admin),
    )
    assert r.status_code == 403
    db_session.refresh(doctor)
    assert doctor.clinic_id is None


def test_rt2_clinic_admin_cannot_relink_patient_user(client, db_session):
    c1 = _clinic(db_session, "Relink-C1")
    admin = _user(db_session, email="relink.admin@test.gn", role="clinic_admin", clinic_id=c1.id)
    victim = _user(db_session, email="victim@test.gn", role="patient", clinic_id=c1.id)
    other = _user(db_session, email="other@test.gn", role="patient", clinic_id=c1.id)
    patient = models.Patient(
        user_id=victim.id,
        first_name="V",
        last_name="P",
        age=40,
        gender="m",
        clinic_id=c1.id,
    )
    db_session.add(patient)
    db_session.commit()
    r = client.put(
        f"/patients/{patient.id}",
        json={
            "user_id": other.id,
            "first_name": "V",
            "last_name": "P",
            "age": 40,
            "gender": "m",
        },
        headers=_auth(admin),
    )
    assert r.status_code == 403
    db_session.refresh(patient)
    assert patient.user_id == victim.id


def test_rt2_medicine_delivery_rejects_foreign_patient(db_session):
    from schemas.clinical import DoctorMedicineDeliveryCreate
    from services.doctor_medicine_delivery_service import DoctorMedicineDeliveryService

    c1 = _clinic(db_session, "Del-C1")
    c2 = _clinic(db_session, "Del-C2")
    pharm = _user(db_session, email="pharm.del@test.gn", role="pharmacist", clinic_id=c1.id)
    foreign = _patient(db_session, clinic_id=c2.id, name="Foreign")
    payload = DoctorMedicineDeliveryCreate(
        patient_name="Foreign",
        patient_id=foreign.id,
        medicine_name="Paracetamol",
        quantity=1,
        doctor_name="Dr X",
    )
    with pytest.raises(Exception):
        DoctorMedicineDeliveryService.create_delivery(
            db_session, clinic_id=c1.id, payload=payload, actor=pharm
        )
