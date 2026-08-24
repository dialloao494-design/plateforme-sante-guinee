"""Reception service request → billing lookup + surgical acts + invoice footer."""

from __future__ import annotations

import inspect
import uuid

import models
from core.provisioning_context import provisioning_channel
from data.aasma_billing_catalog import SURGICAL_ACTS
from security import create_access_token, hash_password
from services import clinic_print_header, invoice_pdf_builder
from services.invoice_pdf_builder import build_hospital_invoice_pdf


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


def _seed_clinic_admin(db_session):
    suffix = uuid.uuid4().hex[:8]
    clinic = models.Clinic(name=f"Recep SR Clinic {suffix}", city="Conakry", is_active=True)
    db_session.add(clinic)
    db_session.commit()
    db_session.refresh(clinic)
    with provisioning_channel("test_fixture"):
        admin = models.User(
            email=f"recep.sr.{suffix}@test.gn",
            hashed_password=hash_password("StrongPass12!"),
            role="clinic_admin",
            clinic_id=clinic.id,
            is_active=True,
            token_version=0,
        )
        db_session.add(admin)
        db_session.commit()
        db_session.refresh(admin)
    patient = models.Patient(
        first_name="Aissatou",
        last_name="Bah",
        age=30,
        gender="f",
        clinic_id=clinic.id,
    )
    db_session.add(patient)
    db_session.commit()
    db_session.refresh(patient)
    return clinic, admin, patient


def test_service_request_persists_pricing_and_lookup(client, db_session):
    _clinic, admin, patient = _seed_clinic_admin(db_session)
    headers = _auth(admin)

    create = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "surgery",
            "service_name": "Suture simple",
            "catalog_code": "suture_simple",
            "charge_type": "procedure",
            "unit_price_gnf": 150000,
            "status": "pending",
        },
        headers=headers,
    )
    assert create.status_code == 201, create.text
    body = create.json()
    assert body["request_number"].startswith("DSR-")
    assert body["unit_price_gnf"] == 150000
    assert body["service_category"] == "surgery"

    lookup = client.get(
        "/clinical/reception/his/service-requests/lookup",
        params={"q": body["request_number"]},
        headers=headers,
    )
    assert lookup.status_code == 200, lookup.text
    assert lookup.json()["id"] == body["id"]
    assert lookup.json()["service_name"] == "Suture simple"


def test_consultation_service_request_category_accepted(client, db_session):
    _clinic, admin, patient = _seed_clinic_admin(db_session)
    r = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "consultation",
            "service_name": "Consultation spécialisée — Médecine",
            "catalog_code": "medicine",
            "charge_type": "consultation",
            "unit_price_gnf": 250000,
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text


def test_billing_catalog_includes_surgical_acts(client, db_session):
    _clinic, admin, _patient = _seed_clinic_admin(db_session)
    r = client.get("/clinical/reception/his/billing-catalog", headers=_auth(admin))
    assert r.status_code == 200, r.text
    acts = r.json().get("surgical_acts") or []
    assert len(acts) == len(SURGICAL_ACTS)
    assert "Chirurgie" in (r.json().get("billing_departments") or [])


def test_hospitalization_request_uses_confirmed_rate_and_duration(client, db_session):
    _clinic, admin, patient = _seed_clinic_admin(db_session)
    headers = _auth(admin)
    created = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id,
            "service_category": "hospitalization",
            "service_name": "Hospitalisation médecine",
            "catalog_code": "hospitalization_standard",
            "duration_value": 2,
            "duration_unit": "days",
            "specialty_code": "medicine",
            "accommodation_type": "standard_bed",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    request = created.json()
    assert request["unit_price_gnf"] == 200_000
    assert request["quantity"] == 2
    assert request["duration_value"] == 2
    assert "Médecine" in request["service_name"]

    invoice = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Hospitalisation",
            "items": [{
                "source_type": "service_request",
                "source_ref": request["request_number"],
                "catalog_code": request["catalog_code"],
                "quantity": 1,
            }],
        },
        headers=headers,
    )
    assert invoice.status_code == 201, invoice.text
    assert invoice.json()["subtotal_amount_gnf"] == 400_000
    assert invoice.json()["items"][0]["quantity"] == 2


def test_private_cabin_rate_and_pediatric_hospitalization_exclusion(client, db_session):
    _clinic, admin, patient = _seed_clinic_admin(db_session)
    headers = _auth(admin)
    catalog = client.get("/clinical/reception/his/billing-catalog", headers=headers).json()
    prices = {row["code"]: row["price_gnf"] for row in catalog["hospitalization_services"]}
    assert prices == {"hospitalization_standard": 200_000, "hospitalization_private_cabin": 500_000}
    pediatric = client.post(
        "/clinical/reception/his/service-requests",
        json={
            "patient_id": patient.id, "service_category": "hospitalization",
            "service_name": "Hospitalisation pédiatrie", "catalog_code": "hospitalization_standard",
            "duration_value": 1, "duration_unit": "days", "specialty_code": "pediatrics",
            "accommodation_type": "standard_bed",
        },
        headers=headers,
    )
    assert pediatric.status_code == 400


def test_reception_admission_persists_one_placement(client, db_session):
    _clinic, admin, patient = _seed_clinic_admin(db_session)
    response = client.post(
        "/clinical/reception/his/admissions",
        json={
            "patient_id": patient.id, "admission_date": "2026-08-24",
            "services": ["Hospitalisation"], "admission_type": "hospitalization",
            "bed_number": "7",
        },
        headers=_auth(admin),
    )
    assert response.status_code == 201, response.text
    assert response.json()["bed_number"] == "7"
    assert response.json()["cabin_number"] is None

    missing_placement = client.post(
        "/clinical/reception/his/admissions",
        json={
            "patient_id": patient.id, "admission_date": "2026-08-24",
            "services": ["Hospitalisation"], "admission_type": "outpatient",
        },
        headers=_auth(admin),
    )
    assert missing_placement.status_code == 422


def test_invoice_pdf_footer_keeps_printed_by_without_address():
    pdf = build_hospital_invoice_pdf(
        invoice_number="FAC-TEST-001",
        patient_name="Test Patient",
        patient_file_number="P-1",
        items=[
            {
                "description": "Suture simple",
                "quantity": 1,
                "unit_price_gnf": 150000,
                "amount_gnf": 150000,
            }
        ],
        subtotal=150000,
        exemption_percent=0,
        exemption_amount=0,
        total=150000,
        paid=0,
        printed_by="RECEPTIONIST",
        printed_date="30/07/2026",
        printed_time="23:45",
    )
    assert isinstance(pdf, (bytes, bytearray))
    assert len(pdf) > 500
    source = inspect.getsource(invoice_pdf_builder.build_hospital_invoice_pdf)
    assert "Imprimé par" in source
    assert "printed_date" in source and "printed_time" in source
    assert "CLINIC_FOOTER_LINE" not in source
    assert "CLINIC_FOOTER_LINE" not in invoice_pdf_builder.__dict__


def test_clinic_motto_style_is_nine_point():
    source = inspect.getsource(clinic_print_header.append_official_clinic_header)
    assert "fontSize=9" in source
    assert 'CLINIC_MOTTO' in source or "Travail" in source or "motto" in source.lower()
