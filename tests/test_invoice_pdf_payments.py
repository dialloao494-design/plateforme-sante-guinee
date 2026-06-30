"""Tests for invoice PDF payment breakdown."""

from services.pdf_service import invoice_pdf


def test_invoice_pdf_lists_each_payment_separately():
    pdf = invoice_pdf(
        "FAC-001",
        "Jean Dupont",
        [{"description": "Consultation", "quantity": 1, "unit_price_gnf": 350000, "amount_gnf": 350000}],
        subtotal=350000,
        total=350000,
        paid=350000,
        payment_lines=[
            {"payment_method": "orange_money", "amount_gnf": 100000, "reference": "OM123456"},
            {"payment_method": "cash", "amount_gnf": 50000},
            {"payment_method": "insurance", "amount_gnf": 200000},
        ],
        printed_by="Caissier Test",
        printed_at="30/06/2026 10:00",
    )
    text = pdf.decode("latin-1", errors="replace")
    assert b"Orange Money" in pdf or "Orange Money" in text
    assert "100 000 GNF" in text
    assert "Esp" in text and "50 000 GNF" in text
    assert "Assurance" in text and "200 000 GNF" in text
    assert "Total pay" in text and "350 000 GNF" in text
    assert "Reste" in text and "0 GNF" in text


def test_invoice_pdf_legacy_payment_methods_fallback():
    pdf = invoice_pdf(
        "FAC-002",
        "Marie Konate",
        [{"description": "Labo", "amount_gnf": 50000}],
        subtotal=50000,
        total=50000,
        paid=50000,
        payment_methods=["cash"],
        printed_by="Reception",
        printed_at="30/06/2026 11:00",
    )
    assert b"cash" in pdf
    assert b"50 000 GNF" in pdf
    assert b"Montant re" in pdf
