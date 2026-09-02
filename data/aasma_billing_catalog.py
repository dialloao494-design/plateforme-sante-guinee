"""AASMA billing catalog — consultations, imaging, and service types for reception."""

from __future__ import annotations

# Admission / visit services (multi-select)
ADMISSION_SERVICES = [
    {"code": "emergency_consultation", "label": "Consultation urgences"},
    {"code": "specialized_consultation", "label": "Consultation spécialisée"},
    {"code": "outpatient_consultation", "label": "Consultation externe"},
    {"code": "laboratory", "label": "Laboratoire"},
    {"code": "pharmacy", "label": "Pharmacie"},
    {"code": "hospitalization", "label": "Hospitalisation"},
    {"code": "medical_imaging", "label": "Imagerie médicale"},
]

# Billable consultation types (default prices in GNF)
# Specialized adult default = 250 000; pediatrics overrides via specialty.price_gnf.
CONSULTATION_SERVICES = [
    {
        "code": "emergency_consultation",
        "label": "Consultation d'urgences",
        "charge_type": "consultation",
        "price_gnf": 150_000,
    },
    {
        "code": "specialized_consultation",
        "label": "Consultation spécialisée",
        "charge_type": "consultation",
        "price_gnf": 250_000,
        "requires_specialty": True,
    },
    {
        "code": "outpatient_consultation",
        "label": "Consultation externe",
        "charge_type": "consultation",
        "price_gnf": 100_000,
    },
    {
        "code": "hospitalization",
        "label": "Hospitalisation (forfait journalier)",
        "charge_type": "hospitalization",
        "price_gnf": 350_000,
    },
    {
        "code": "pediatric_emergency_care",
        "label": "Soins d'urgence pédiatrie",
        "charge_type": "procedure",
        "price_gnf": 250_000,
    },
]

# Hospitalization tariffs confirmed by the clinic. The two pediatric prices are
# distinct accommodation types; the two shared-room prices intentionally retain
# their clinic-provided rate as the visible distinction.
HOSPITALIZATION_SERVICES = [
    {"code": "hospitalization_shared_room_180", "label": "Hospitalisation — lit salle commune (tarif 180 000)", "charge_type": "hospitalization", "price_gnf": 180_000},
    {"code": "hospitalization_standard", "label": "Hospitalisation — lit salle commune (tarif 200 000)", "charge_type": "hospitalization", "price_gnf": 200_000},
    {"code": "hospitalization_private_cabin", "label": "Hospitalisation — cabine VIP", "charge_type": "hospitalization", "price_gnf": 500_000},
    {"code": "hospitalization_pediatric_cradle", "label": "Hospitalisation — lit pédiatrie berceau nouveau-né", "charge_type": "hospitalization", "price_gnf": 80_000},
    {"code": "hospitalization_pediatric_bed", "label": "Hospitalisation — lit pédiatrie", "charge_type": "hospitalization", "price_gnf": 120_000},
]

# Clinic tariff sheet (20-07-26):
# Médecine / Neurochirurgie / Chirurgie / MIT / Gynéco / Traumato :
#   spécialisée 250 000 · urgences 150 000
# Pédiatrie : spécialisée 200 000 · urgence 100 000 · soins urgences 250 000
SPECIALIZED_SPECIALTIES = [
    {
        "code": "medicine",
        "label": "Médecine",
        "price_gnf": 250_000,
        "emergency_price_gnf": 150_000,
    },
    {
        "code": "neurosurgery",
        "label": "Neurochirurgie",
        "price_gnf": 250_000,
        "emergency_price_gnf": 150_000,
    },
    {
        "code": "surgery",
        "label": "Chirurgie",
        "price_gnf": 250_000,
        "emergency_price_gnf": 150_000,
    },
    {
        "code": "infectious_tropical",
        "label": "MIT (Maladies infectieuses & tropicales)",
        "price_gnf": 250_000,
        "emergency_price_gnf": 150_000,
    },
    {
        "code": "gynecology_obstetrics",
        "label": "Gynécologie & Obstétrique",
        "price_gnf": 250_000,
        "emergency_price_gnf": 150_000,
    },
    {
        "code": "traumatology",
        "label": "Traumatologie",
        "price_gnf": 250_000,
        "emergency_price_gnf": 150_000,
    },
    {
        "code": "pediatrics",
        "label": "Pédiatrie",
        "price_gnf": 200_000,
        "emergency_price_gnf": 100_000,
        "emergency_care_price_gnf": 250_000,
    },
    # Kept for compatibility with existing admissions / doctor routing
    {
        "code": "pediatric_surgery",
        "label": "Chirurgie pédiatrique",
        "price_gnf": 200_000,
        "emergency_price_gnf": 100_000,
    },
    {
        "code": "internal_medicine",
        "label": "Médecine interne",
        "price_gnf": 250_000,
        "emergency_price_gnf": 150_000,
    },
    {
        "code": "orthopedic_trauma",
        "label": "Chirurgie orthopédique & traumatologique",
        "price_gnf": 250_000,
        "emergency_price_gnf": 150_000,
    },
]

# Medical imaging examinations — configurable prices
IMAGING_EXAMINATIONS = [
    {"code": "xray", "label": "Radiographie (X-Ray)", "modality": "xray", "price_gnf": 150_000},
    {"code": "ultrasound", "label": "Échographie", "modality": "ultrasound", "price_gnf": 200_000},
    {"code": "ct_scan", "label": "Scanner (CT Scan)", "modality": "ct_scan", "price_gnf": 450_000},
    {"code": "mri", "label": "IRM (MRI)", "modality": "mri", "price_gnf": 750_000},
    {"code": "mammography", "label": "Mammographie", "modality": "mammography", "price_gnf": 250_000},
    {"code": "dental_panoramic", "label": "Panoramique dentaire", "modality": "dental_panoramic", "price_gnf": 180_000},
]

# Nursing / care prestations from clinic tariff sheet + ambulance
SERVICE_PRESTATIONS = [
    {"code": "emergency_care_with_serum", "label": "Soins d'urgence avec sérum", "price_gnf": 500_000},
    {"code": "injection", "label": "Injection", "price_gnf": 25_000},
    {"code": "small_dressing", "label": "Petit pansement", "price_gnf": 30_000},
    {"code": "large_dressing", "label": "Grand pansement", "price_gnf": 80_000},
    {"code": "pediatric_emergency_care", "label": "Soins d'urgence pédiatrie", "price_gnf": 250_000},
    {"code": "medical_transport_ambulance", "label": "Transport médical / Ambulance", "price_gnf": 0},
]

# Surgical acts available in reception service requests / billing
SURGICAL_ACTS = [
    {"code": "small_dressing", "label": "Petit pansement", "price_gnf": 30_000},
    {"code": "large_dressing", "label": "Grand pansement", "price_gnf": 80_000},
    {"code": "skin_graft", "label": "Greffe cutanée", "price_gnf": 0},
    {"code": "suture_simple", "label": "Suture simple", "price_gnf": 150_000},
    {"code": "suture_complex", "label": "Suture complexe", "price_gnf": 300_000},
    {"code": "abscess_drainage", "label": "Drainage d'abcès", "price_gnf": 200_000},
    {"code": "circumcision", "label": "Circoncision", "price_gnf": 250_000},
    {"code": "hernia_repair", "label": "Cure de hernie", "price_gnf": 800_000},
    {"code": "appendectomy", "label": "Appendicectomie", "price_gnf": 1_200_000},
    {"code": "cesarean", "label": "Césarienne", "price_gnf": 1_500_000},
    {"code": "wound_debridement", "label": "Parage / débridement", "price_gnf": 250_000},
    {"code": "minor_surgery", "label": "Petite chirurgie", "price_gnf": 350_000},
    {"code": "exploration_laparo", "label": "Exploration chirurgicale", "price_gnf": 1_000_000},
]

BILLING_DEPARTMENTS = [
    "Consultation urgences",
    "Consultation spécialisée",
    "Consultation externe",
    "Laboratoire",
    "Pharmacie",
    "Hospitalisation",
    "Imagerie médicale",
    "Urgences",
    "Soins infirmiers",
    "Chirurgie",
]


def _charge_type_for_catalog_bucket(bucket: str) -> str:
    mapping = {
        "consultation": "consultation",
        "specialty": "consultation",
        "imaging": "radiology",
        "prestation": "nursing",
        "surgery": "procedure",
    }
    return mapping.get(bucket, "procedure")


def resolve_billing_catalog_item(
    catalog_code: str | None,
    *,
    price_variant: str | None = None,
) -> dict | None:
    """Resolve an authoritative AASMA catalog row by code.

    Returns dict with keys: code, label, price_gnf, charge_type, bucket.

    ``price_variant`` selects specialized vs emergency tariffs for specialty codes:
    - ``None`` / ``"specialized"`` → Consultation spécialisée + price_gnf
    - ``"emergency"`` → Consultation d'urgences + emergency_price_gnf
    """
    code = (catalog_code or "").strip()
    if not code:
        return None

    variant = (price_variant or "").strip().lower() or None
    if variant not in (None, "specialized", "emergency"):
        variant = None

    for row in HOSPITALIZATION_SERVICES:
        if row.get("code") == code:
            return {"code": code, "label": row["label"], "price_gnf": int(row["price_gnf"]),
                    "charge_type": "hospitalization", "bucket": "hospitalization"}

    for row in CONSULTATION_SERVICES:
        if row.get("code") == code:
            return {
                "code": code,
                "label": row["label"],
                "price_gnf": int(row.get("price_gnf") or 0),
                "charge_type": row.get("charge_type") or "consultation",
                "bucket": "consultation",
            }

    for row in SPECIALIZED_SPECIALTIES:
        if row.get("code") == code:
            if variant == "emergency":
                return {
                    "code": code,
                    "label": f"Consultation d'urgences — {row['label']}",
                    "price_gnf": int(
                        row.get("emergency_price_gnf")
                        or next(
                            (
                                c.get("price_gnf")
                                for c in CONSULTATION_SERVICES
                                if c.get("code") == "emergency_consultation"
                            ),
                            150_000,
                        )
                    ),
                    "charge_type": "consultation",
                    "bucket": "specialty",
                    "price_variant": "emergency",
                }
            return {
                "code": code,
                "label": f"Consultation spécialisée — {row['label']}",
                "price_gnf": int(row.get("price_gnf") or 0),
                "charge_type": "consultation",
                "bucket": "specialty",
                "price_variant": "specialized",
            }

    for row in IMAGING_EXAMINATIONS:
        if row.get("code") == code:
            return {
                "code": code,
                "label": row["label"],
                "price_gnf": int(row.get("price_gnf") or 0),
                "charge_type": "radiology",
                "bucket": "imaging",
            }

    for row in SERVICE_PRESTATIONS:
        if row.get("code") == code:
            return {
                "code": code,
                "label": row["label"],
                "price_gnf": int(row.get("price_gnf") or 0),
                "charge_type": _charge_type_for_catalog_bucket("prestation"),
                "bucket": "prestation",
            }

    for row in SURGICAL_ACTS:
        if row.get("code") == code:
            return {
                "code": code,
                "label": row["label"],
                "price_gnf": int(row.get("price_gnf") or 0),
                "charge_type": "procedure",
                "bucket": "surgery",
            }

    # Laboratory — AASMA tariff sheet (authoritative prices).
    try:
        from data.aasma_lab_catalog import AASMA_LAB_CATALOG

        for row in AASMA_LAB_CATALOG:
            if row.get("code") == code:
                return {
                    "code": code,
                    "label": row.get("name") or code,
                    "price_gnf": int(row.get("price_gnf") or 0),
                    "charge_type": "lab",
                    "bucket": "laboratory",
                }
    except Exception:
        pass

    # Legacy short lab codes (NFS, GLY, …) — map onto AASMA rows when possible.
    try:
        from data.lab_test_catalog import LAB_TEST_CATALOG
        from data.aasma_lab_catalog import AASMA_LAB_CATALOG

        legacy = next((r for r in LAB_TEST_CATALOG if r.get("code") == code), None)
        if legacy:
            needle = code.lower()
            name_needle = (legacy.get("name") or "").lower()
            for row in AASMA_LAB_CATALOG:
                hay = f"{row.get('code', '')} {row.get('name', '')}".lower()
                if needle in hay or (name_needle and name_needle[:12] in hay):
                    return {
                        "code": row["code"],
                        "label": row.get("name") or legacy.get("name") or code,
                        "price_gnf": int(row.get("price_gnf") or 0),
                        "charge_type": "lab",
                        "bucket": "laboratory",
                    }
    except Exception:
        pass

    return None
