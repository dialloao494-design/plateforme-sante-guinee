"""Clinical regression pilot — invoice PDF fields, TPN, session idle, doctor surgical catalog."""

from __future__ import annotations

from pathlib import Path

from data.aasma_billing_catalog import IMAGING_EXAMINATIONS, SERVICE_PRESTATIONS, SURGICAL_ACTS
from services.invoice_pdf_builder import build_hospital_invoice_pdf
from services.pdf_service import invoice_pdf


def _pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from a simple ReportLab PDF for field assertions."""
    # Prefer pypdf / PyPDF2 when available; fall back to latin-1 raw scan.
    try:
        from pypdf import PdfReader  # type: ignore
    except Exception:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except Exception:
            return pdf_bytes.decode("latin-1", errors="ignore")

    from io import BytesIO

    reader = PdfReader(BytesIO(pdf_bytes))
    parts = []
    for page in reader.pages:
        parts.append(page.extract_text() or "")
    return "\n".join(parts)


def test_invoice_pdf_contains_required_identity_fields():
    pdf_bytes = build_hospital_invoice_pdf(
        invoice_number="INV-2026-001-00099",
        patient_name="Fatoumata Camara",
        patient_file_number="AASMA-001-00042",
        items=[{"description": "Consultation", "quantity": 1, "unit_price_gnf": 50000, "amount_gnf": 50000}],
        subtotal=50000,
        exemption_percent=0,
        exemption_amount=0,
        total=50000,
        paid=50000,
        payment_details=[{"method": "cash", "label": "Espèces", "amount_gnf": 50000}],
        printed_by="Reception Demo",
        printed_date="06/08/2026",
        printed_time="14:30",
        invoice_date="06/08/2026",
        invoice_time="10:15",
        cashier="Caissier Demo",
    )
    assert pdf_bytes[:4] == b"%PDF"
    text = _pdf_text(pdf_bytes)
    for needle in (
        "INV-2026-001-00099",
        "Fatoumata Camara",
        "AASMA-001-00042",
        "06/08/2026",
        "10:15",
        "Caissier Demo",
        "Reception Demo",
        "14:30",
    ):
        assert needle in text, f"Missing invoice field in PDF text: {needle!r}\n---\n{text[:800]}"


def test_invoice_pdf_service_wrapper_passes_date_and_cashier():
    pdf_bytes = invoice_pdf(
        "INV-WRAP-1",
        "Patient Test",
        [{"description": "Lab", "quantity": 1, "unit_price_gnf": 10000, "amount_gnf": 10000}],
        subtotal=10000,
        total=10000,
        paid=10000,
        printed_by="Printer User",
        printed_date="01/01/2026",
        printed_time="09:00",
        patient_file_number="DOS-1",
        invoice_date="31/12/2025",
        invoice_time="18:45",
        cashier="Cashier User",
    )
    text = _pdf_text(pdf_bytes)
    assert "INV-WRAP-1" in text
    assert "Patient Test" in text
    assert "DOS-1" in text
    assert "31/12/2025" in text
    assert "18:45" in text
    assert "Cashier User" in text
    assert "Printer User" in text


def test_billing_catalog_includes_tpn_and_surgical_acts():
    tpn_imaging = [r for r in IMAGING_EXAMINATIONS if r["code"] == "tpn"]
    tpn_service = [r for r in SERVICE_PRESTATIONS if r["code"] == "tpn"]
    assert tpn_imaging, "TPN missing from IMAGING_EXAMINATIONS"
    assert tpn_service, "TPN missing from SERVICE_PRESTATIONS"
    assert any(a["code"] == "suture_simple" for a in SURGICAL_ACTS)
    assert all("code" in a and "label" in a and "price_gnf" in a for a in SURGICAL_ACTS)


def test_session_idle_default_is_five_minutes():
    cfg = Path("frontend-sante/frontend/src/utils/sessionConfig.js").read_text(encoding="utf-8")
    assert "export const SESSION_IDLE_MINUTES = parseMinutes(" in cfg
    assert "VITE_SESSION_IDLE_MINUTES" in cfg
    # Default idle minutes argument must be 5 for pilot clinic (not the old 30).
    idle_block = cfg.split("SESSION_IDLE_MINUTES = parseMinutes(")[1].split(");")[0]
    assert "5" in idle_block
    assert "30" not in idle_block


def test_nurse_dashboard_vitals_before_motif_and_extended_fields():
    src = Path("frontend-sante/frontend/src/pages/clinical/NurseDashboard.jsx").read_text(encoding="utf-8")
    vitals_idx = src.index("<legend>Signes vitaux</legend>")
    motif_idx = src.index("<legend>Motif de consultation</legend>")
    assert vitals_idx < motif_idx, "Vital signs must appear before consultation reason"
    hist_idx = src.index("<legend>Antécédents</legend>")
    rx_idx = src.index("<legend>Prescription</legend>")
    hosp_idx = src.index("<legend>Signes vitaux des patients hospitalisés (soins quotidiens)</legend>")
    notes_idx = src.index("<legend>Notes infirmières</legend>")
    assert hist_idx < rx_idx < hosp_idx < notes_idx
    assert "spo2_percent" in src
    assert "muac_cm" in src
    assert "head_circumference_cm" in src
    assert "Keep patient selected" in src or "loadPatientHistory(selectedPatient.id)" in src
    assert "setSelectedPatient(null)" not in src.split("saveAssessment")[1].split("statCards")[0]


def test_doctor_dashboard_has_surgical_acts_table_and_extended_vitals():
    src = Path("frontend-sante/frontend/src/pages/clinical/DoctorClinicalDashboard.jsx").read_text(
        encoding="utf-8"
    )
    assert "Actes chirurgicaux — table avec codes" in src
    assert "surgical_acts" in src
    assert "spo2_percent" in src
    assert "muac_cm" in src
    assert "head_circumference_cm" in src


def test_discharge_auth_css_targets_one_a4_page():
    css = Path("frontend-sante/frontend/src/components/print/print-documents.css").read_text(
        encoding="utf-8"
    )
    block = css.split("/* —— Autorisation de sortie")[1].split("@media print")[0]
    assert "max-height: 277mm" in block
    assert "page-break-inside: avoid" in block
    assert "font-size: 9.5pt" in block


def test_http_client_refreshes_on_401():
    src = Path("frontend-sante/frontend/src/services/httpClient.js").read_text(encoding="utf-8")
    assert "/auth/refresh" in src or "auth/refresh" in src
    assert "getRefreshToken" in src
    assert "setAuthToken" in src


def test_doctor_catalog_exposes_surgical_acts(client, db_session, admin_user):
    import models
    from core.provisioning_context import provisioning_channel
    from security import create_access_token, hash_password

    clinic = models.Clinic(name="Doc Catalog Clinic", address="Test")
    db_session.add(clinic)
    db_session.flush()
    doctor_user = models.User(
        email=f"doc.catalog.{admin_user.id}@test.com",
        hashed_password=hash_password("DoctorTest1!"),
        role="doctor",
        clinic_id=clinic.id,
    )
    with provisioning_channel("test_fixture"):
        db_session.add(doctor_user)
        db_session.commit()
        db_session.refresh(doctor_user)
    token = create_access_token(
        {
            "sub": doctor_user.email,
            "user_id": doctor_user.id,
            "user_role": doctor_user.role,
            "role": doctor_user.role,
        }
    )
    r = client.get(
        "/clinical/doctor/catalog",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    acts = body.get("surgical_acts") or []
    assert len(acts) >= 5
    assert any(a.get("code") == "suture_simple" for a in acts)
