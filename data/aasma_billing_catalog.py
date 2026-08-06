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
    # Requested clinic examination / care line (nutrition parentérale totale).
    {"code": "tpn", "label": "TPN (nutrition parentérale totale)", "modality": "other", "price_gnf": 500_000},
]

# Nursing / care prestations from clinic tariff sheet + ambulance
SERVICE_PRESTATIONS = [
    {"code": "emergency_care_with_serum", "label": "Soins d'urgence avec sérum", "price_gnf": 500_000},
    {"code": "injection", "label": "Injection", "price_gnf": 25_000},
    {"code": "small_dressing", "label": "Petit pansement", "price_gnf": 30_000},
    {"code": "large_dressing", "label": "Grand pansement", "price_gnf": 80_000},
    {"code": "pediatric_emergency_care", "label": "Soins d'urgence pédiatrie", "price_gnf": 250_000},
    {"code": "tpn", "label": "TPN (nutrition parentérale totale)", "price_gnf": 500_000},
    {"code": "medical_transport_ambulance", "label": "Transport médical / Ambulance", "price_gnf": 0},
]

# Surgical acts available in reception / doctor service requests / billing.
# clinic_code = code clinique AASMA affiché (ex. QAASMA-PP pour Parage).
SURGICAL_ACTS = [
    {"code": "suture_simple", "clinic_code": "QAASMA-SS", "label": "Suture simple", "price_gnf": 150_000},
    {"code": "suture_complex", "clinic_code": "QAASMA-SC", "label": "Suture complexe", "price_gnf": 300_000},
    {"code": "abscess_drainage", "clinic_code": "QAASMA-DA", "label": "Drainage d'abcès", "price_gnf": 200_000},
    {"code": "circumcision", "clinic_code": "QAASMA-CI", "label": "Circoncision", "price_gnf": 250_000},
    {"code": "hernia_repair", "clinic_code": "QAASMA-CH", "label": "Cure de hernie", "price_gnf": 800_000},
    {"code": "appendectomy", "clinic_code": "QAASMA-AP", "label": "Appendicectomie", "price_gnf": 1_200_000},
    {"code": "cesarean", "clinic_code": "QAASMA-CS", "label": "Césarienne", "price_gnf": 1_500_000},
    {"code": "wound_debridement", "clinic_code": "QAASMA-PP", "label": "Parage", "price_gnf": 250_000},
    {"code": "minor_surgery", "clinic_code": "QAASMA-PC", "label": "Petite chirurgie", "price_gnf": 350_000},
    {"code": "exploration_laparo", "clinic_code": "QAASMA-EX", "label": "Exploration chirurgicale", "price_gnf": 1_000_000},
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


def resolve_billing_catalog_item(catalog_code: str | None) -> dict | None:
    """Resolve an authoritative AASMA catalog row by code.

    Returns dict with keys: code, label, price_gnf, charge_type, bucket.
    """
    code = (catalog_code or "").strip()
    if not code:
        return None

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
            return {
                "code": code,
                "label": f"Consultation spécialisée — {row['label']}",
                "price_gnf": int(row.get("price_gnf") or 0),
                "charge_type": "consultation",
                "bucket": "specialty",
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
        if row.get("code") == code or row.get("clinic_code") == code:
            return {
                "code": row["code"],
                "clinic_code": row.get("clinic_code") or row["code"],
                "label": row["label"],
                "price_gnf": int(row.get("price_gnf") or 0),
                "charge_type": "procedure",
                "bucket": "surgery",
            }

    return None
