"""Regression: emergency specialty must not flip to specialized on invoice create.

Clinic report (08-08-26): selecting Urgences + specialty records the draft line
correctly, but « Créer la facture » rewrote it as Consultation spécialisée.
"""

from __future__ import annotations

from data.aasma_billing_catalog import resolve_billing_catalog_item
from tests.test_billing_integrity_hardening import _auth, _seed


def test_resolve_emergency_variant_uses_emergency_tariff():
    row = resolve_billing_catalog_item("medicine", price_variant="emergency")
    assert row is not None
    assert row["label"] == "Consultation d'urgences — Médecine"
    assert row["price_gnf"] == 150_000
    assert row["price_variant"] == "emergency"


def test_resolve_specialized_default_unchanged():
    row = resolve_billing_catalog_item("medicine")
    assert row is not None
    assert row["label"] == "Consultation spécialisée — Médecine"
    assert row["price_gnf"] == 250_000


def test_resolve_pediatrics_emergency_tariff():
    row = resolve_billing_catalog_item("pediatrics", price_variant="emergency")
    assert row is not None
    assert row["label"] == "Consultation d'urgences — Pédiatrie"
    assert row["price_gnf"] == 100_000


def test_invoice_create_emergency_specialty_keeps_label_and_price(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Consultation urgences",
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "Consultation d'urgences — Médecine",
                    "quantity": 1,
                    "catalog_code": "medicine",
                    "price_variant": "emergency",
                }
            ],
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["department"] == "Consultation urgences"
    assert body["total_amount_gnf"] == 150_000
    items = body.get("items") or []
    assert len(items) == 1
    assert items[0]["description"] == "Consultation d'urgences — Médecine"
    assert items[0]["unit_price_gnf"] == 150_000


def test_invoice_create_infers_emergency_from_department_without_variant(client, db_session):
    """Older clients may omit price_variant; department context selects emergency tariff."""
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Consultation urgences",
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "ignored — server authoritative",
                    "quantity": 1,
                    "catalog_code": "medicine",
                }
            ],
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_amount_gnf"] == 150_000
    assert body["items"][0]["description"] == "Consultation d'urgences — Médecine"


def test_invoice_create_specialized_still_uses_specialized_tariff(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Consultation spécialisée",
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "Consultation spécialisée — Médecine",
                    "quantity": 1,
                    "catalog_code": "medicine",
                    "price_variant": "specialized",
                }
            ],
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_amount_gnf"] == 250_000
    assert body["items"][0]["description"] == "Consultation spécialisée — Médecine"


def test_invoice_rejects_emergency_variant_under_specialized_department(client, db_session):
    """Client cannot select the cheaper emergency tariff on a specialized invoice."""
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Consultation spécialisée",
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "Consultation spécialisée — Médecine",
                    "quantity": 1,
                    "catalog_code": "medicine",
                    "price_variant": "emergency",
                }
            ],
        },
        headers=_auth(admin),
    )
    assert r.status_code == 400, r.text
    assert "incompatible" in r.text.lower() or "emergency" in r.text.lower()


def test_invoice_rejects_emergency_variant_without_emergency_department(client, db_session):
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Consultation externe",
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "spoof urgence in text",
                    "quantity": 1,
                    "catalog_code": "medicine",
                    "price_variant": "emergency",
                }
            ],
        },
        headers=_auth(admin),
    )
    assert r.status_code == 400, r.text


def test_invoice_ignores_urgence_in_description_under_specialized_department(client, db_session):
    """Free-text description must not unlock the emergency tariff."""
    _clinic, admin, patient, *_ = _seed(db_session)
    r = client.post(
        "/clinical/reception/his/invoices",
        json={
            "patient_id": patient.id,
            "department": "Consultation spécialisée",
            "items": [
                {
                    "charge_type": "consultation",
                    "description": "Consultation d'urgences — Médecine",
                    "quantity": 1,
                    "catalog_code": "medicine",
                }
            ],
        },
        headers=_auth(admin),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["total_amount_gnf"] == 250_000
    assert body["items"][0]["description"] == "Consultation spécialisée — Médecine"
