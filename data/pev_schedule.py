"""Guinea PEV (Programme Élargi de Vaccination) — simplified national schedule."""

from __future__ import annotations

# age_months, vaccine_code, vaccine_name, dose_label
DEFAULT_PEV_SCHEDULE: list[dict[str, str | int]] = [
    {"age_months": 0, "vaccine_code": "BCG", "vaccine_name": "BCG", "dose_label": "Naissance"},
    {"age_months": 0, "vaccine_code": "VPO0", "vaccine_name": "VPO", "dose_label": "Dose 0"},
    {"age_months": 0, "vaccine_code": "HEPB0", "vaccine_name": "Hépatite B", "dose_label": "Dose 0"},
    {"age_months": 1, "vaccine_code": "PENTA1", "vaccine_name": "Pentavalent", "dose_label": "Dose 1"},
    {"age_months": 1, "vaccine_code": "VPO1", "vaccine_name": "VPO", "dose_label": "Dose 1"},
    {"age_months": 1, "vaccine_code": "PCV1", "vaccine_name": "Pneumocoque", "dose_label": "Dose 1"},
    {"age_months": 1, "vaccine_code": "ROTA1", "vaccine_name": "Rotavirus", "dose_label": "Dose 1"},
    {"age_months": 2, "vaccine_code": "PENTA2", "vaccine_name": "Pentavalent", "dose_label": "Dose 2"},
    {"age_months": 2, "vaccine_code": "VPO2", "vaccine_name": "VPO", "dose_label": "Dose 2"},
    {"age_months": 2, "vaccine_code": "PCV2", "vaccine_name": "Pneumocoque", "dose_label": "Dose 2"},
    {"age_months": 2, "vaccine_code": "ROTA2", "vaccine_name": "Rotavirus", "dose_label": "Dose 2"},
    {"age_months": 3, "vaccine_code": "PENTA3", "vaccine_name": "Pentavalent", "dose_label": "Dose 3"},
    {"age_months": 3, "vaccine_code": "VPO3", "vaccine_name": "VPO", "dose_label": "Dose 3"},
    {"age_months": 3, "vaccine_code": "PCV3", "vaccine_name": "Pneumocoque", "dose_label": "Dose 3"},
    {"age_months": 3, "vaccine_code": "RR1", "vaccine_name": "Rougeole-Rubéole", "dose_label": "Dose 1"},
    {"age_months": 9, "vaccine_code": "VAA", "vaccine_name": "Fièvre jaune", "dose_label": "Dose unique"},
    {"age_months": 15, "vaccine_code": "VPO4", "vaccine_name": "VPO", "dose_label": "Rappel"},
    {"age_months": 15, "vaccine_code": "RR2", "vaccine_name": "Rougeole-Rubéole", "dose_label": "Dose 2"},
]
