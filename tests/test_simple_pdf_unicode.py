from services.simple_pdf_builder import build_unicode_simple_pdf


def test_simple_pdf_contains_french_text_and_unicode_font():
    pdf = build_unicode_simple_pdf(
        "BON DE SORTIE — Plateforme Santé Guinée",
        [
            "Patient: Fatoumata Camara",
            "Diagnostics: Céphalées / fièvre",
            "Médicaments: Paracétamol 500 mg",
            "Suivi: Contrôle dans 48 heures",
        ],
    )
    assert pdf[:4] == b"%PDF"
    assert b"ClinicSans" in pdf or b"DejaVu" in pdf or b"Identity-H" in pdf
    # Classic mojibake markers must not appear
    assert "SantÃ©".encode("utf-8") not in pdf
    assert "RÃ©publique".encode("utf-8") not in pdf
