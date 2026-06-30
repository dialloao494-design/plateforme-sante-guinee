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
CONSULTATION_SERVICES = [
    {"code": "emergency_consultation", "label": "Consultation urgences", "charge_type": "consultation", "price_gnf": 150_000},
    {"code": "specialized_consultation", "label": "Consultation spécialisée", "charge_type": "consultation", "price_gnf": 200_000},
    {"code": "outpatient_consultation", "label": "Consultation externe", "charge_type": "consultation", "price_gnf": 100_000},
    {"code": "hospitalization", "label": "Hospitalisation (forfait journalier)", "charge_type": "hospitalization", "price_gnf": 350_000},
    {"code": "emergency_care", "label": "Urgences", "charge_type": "procedure", "price_gnf": 175_000},
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

BILLING_DEPARTMENTS = [
    "Consultation urgences",
    "Consultation spécialisée",
    "Consultation externe",
    "Laboratoire",
    "Pharmacie",
    "Hospitalisation",
    "Imagerie médicale",
    "Urgences",
]
