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
]
