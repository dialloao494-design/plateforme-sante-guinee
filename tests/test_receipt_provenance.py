"""Receipt reprinting must preserve the original invoice issuer and timestamp."""
from datetime import datetime
from io import BytesIO

import pytest
from pypdf import PdfReader

import models
from tests.test_reception_service_request_billing import _auth, _seed_clinic_admin


@pytest.mark.parametrize("legacy_midnight", [False, True])
def test_receipt_keeps_issuance_metadata_when_another_operator_reprints(client, db_session, legacy_midnight):
    clinic, issuer, patient = _seed_clinic_admin(db_session)
    _, printer, _ = _seed_clinic_admin(db_session)
    issuer.first_name, issuer.last_name = "Issuing", "Cashier"
    printer.first_name, printer.last_name = "Printing", "Operator"
    printer.clinic_id = clinic.id
    invoice = models.Invoice(
        clinic_id=clinic.id, patient_id=patient.id,
        invoice_number=f"PROVENANCE-{patient.id}", status="issued",
        total_amount_gnf=150000, subtotal_amount_gnf=150000, paid_amount_gnf=0,
        issued_at=datetime(2026, 8, 24, 0 if legacy_midnight else 14, 0 if legacy_midnight else 37),
        created_at=datetime(2026, 8, 24, 16, 42), created_by_user_id=issuer.id,
    )
    db_session.add(invoice)
    db_session.commit()
    response = client.get(f"/clinical/reception/his/invoices/{invoice.id}/receipt", headers=_auth(printer))
    assert response.status_code == 200, response.text
    text = "\n".join(page.extract_text(extraction_mode="layout") for page in PdfReader(BytesIO(response.content)).pages)
    metadata, footer = text.split("Imprimé par", 1)
    assert "24/08/2026" in metadata
    assert ("16:42" if legacy_midnight else "14:37") in metadata
    assert "Issuing Cashier" in metadata
    assert "Printing Operator" not in metadata
    assert "Printing Operator" in footer

    # Receipt metadata must not weaken the existing clinic boundary.
    _, foreign_printer, _ = _seed_clinic_admin(db_session)
    foreign = client.get(f"/clinical/reception/his/invoices/{invoice.id}/receipt", headers=_auth(foreign_printer))
    assert foreign.status_code == 404


def test_receipt_without_known_issuer_does_not_attribute_to_printer(client, db_session):
    clinic, printer, patient = _seed_clinic_admin(db_session)
    printer.first_name, printer.last_name = "Printing", "Operator"
    invoice = models.Invoice(
        clinic_id=clinic.id, patient_id=patient.id,
        invoice_number=f"NO-ISSUER-{patient.id}", status="issued",
        total_amount_gnf=1000, paid_amount_gnf=0,
        issued_at=datetime(2026, 8, 24, 14, 37), created_by_user_id=None,
    )
    db_session.add(invoice)
    db_session.commit()
    response = client.get(f"/clinical/reception/his/invoices/{invoice.id}/receipt", headers=_auth(printer))
    assert response.status_code == 200, response.text
    text = "\n".join(page.extract_text(extraction_mode="layout") for page in PdfReader(BytesIO(response.content)).pages)
    metadata, footer = text.split("Imprimé par", 1)
    assert "Printing Operator" not in metadata
    assert "Printing Operator" in footer


def test_pharmacy_receipt_uses_recorded_charge_provenance(client, db_session):
    clinic, issuer, patient = _seed_clinic_admin(db_session)
    _, printer, _ = _seed_clinic_admin(db_session)
    issuer.first_name, issuer.last_name = "Issuing", "Pharmacist"
    printer.first_name, printer.last_name = "Printing", "Operator"
    printer.clinic_id = clinic.id
    charge = models.ClinicCharge(
        clinic_id=clinic.id, patient_id=patient.id, charge_type="pharmacy",
        source_type="pharmacy_order", source_id=0, description="Synthetic charge",
        amount_gnf=1000, paid_amount_gnf=0, recorded_by_user_id=issuer.id,
        created_at=datetime(2026, 8, 24, 15, 26),
    )
    db_session.add(charge)
    db_session.commit()
    response = client.get(f"/clinical/pharmacy/charges/{charge.id}/receipt", headers=_auth(printer))
    assert response.status_code == 200, response.text
    text = "\n".join(page.extract_text(extraction_mode="layout") for page in PdfReader(BytesIO(response.content)).pages)
    metadata, footer = text.split("Imprimé par", 1)
    assert "24/08/2026" in metadata and "15:26" in metadata
    assert "Issuing Pharmacist" in metadata
    assert "Printing Operator" not in metadata
    assert "Printing Operator" in footer
