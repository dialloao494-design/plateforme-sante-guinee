"""Clinic-17 AASMA plastic-surgery catalogue regression coverage."""

from data.aasma_billing_catalog import (
    SURGICAL_ACTS,
    resolve_billing_catalog_item,
    surgical_acts_for_clinic,
)
from data.aasma_plastic_surgery_catalog import AASMA_PLASTIC_SURGERY_CATALOG


def test_catalog_is_complete_grouped_and_code_unique():
    rows = AASMA_PLASTIC_SURGERY_CATALOG
    codes = [row["code"] for row in rows]

    assert len(rows) == 102
    assert len(codes) == len(set(codes))
    assert {row["section"] for row in rows} == {
        "Générale", "Reconstruction", "Esthétique", "Brûlés"
    }
    assert all(row["department"] == "Chirurgie plastique" for row in rows)
    assert all(0 < row["price_gnf"] <= 28_000_000 for row in rows)


def test_confirmed_and_internal_rows_keep_approved_codes_and_tariffs():
    by_code = {row["code"]: row for row in AASMA_PLASTIC_SURGERY_CATALOG}

    expected = {
        "QAASMA-HospCD": ("Hospitalisation cicatrisation spontanée 1", 50_000),
        "QAASMA-HospCD2": ("Hospitalisation cicatrisation spontanée 2", 150_000),
        "QAASMA-PFreinLang": ("Exérèse frein de langue", 540_000),
        "QAASMA-PLaser": ("Laser séance", 350_000),
        "QAASMA-Append": ("Appendicectomie", 3_700_000),
        "QAASMA-PUretroAnt": ("Urétroplastie antérieure", 13_600_000),
    }
    for code, (label, tariff) in expected.items():
        assert by_code[code]["label"] == label
        assert by_code[code]["price_gnf"] == tariff


def test_catalog_is_scoped_to_clinic_17_and_reconciled_by_code():
    clinic_17 = surgical_acts_for_clinic(17)
    other_clinic = surgical_acts_for_clinic(18)

    assert any(row["code"] == "QAASMA-HospCD2" for row in clinic_17)
    assert not any(row["code"] == "QAASMA-HospCD2" for row in other_clinic)
    assert len({row["code"] for row in clinic_17}) == len(clinic_17)
    assert len(other_clinic) == len(SURGICAL_ACTS)


def test_resolver_enforces_clinic_scope_and_authoritative_tariff():
    assert resolve_billing_catalog_item("QAASMA-Append", clinic_id=18) is None
    resolved = resolve_billing_catalog_item("QAASMA-Append", clinic_id=17)

    assert resolved == {
        "code": "QAASMA-Append",
        "label": "Appendicectomie",
        "price_gnf": 3_700_000,
        "charge_type": "procedure",
        "bucket": "surgery",
    }
