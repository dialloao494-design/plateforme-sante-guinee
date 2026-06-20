"""Guinean PEV paper register field options (registre mensuel / carnet)."""

INJECTION_SITES = [
    {"code": "deltoide_d", "label": "Deltoïde droit"},
    {"code": "deltoide_g", "label": "Deltoïde gauche"},
    {"code": "cuisse_d", "label": "Cuisse droite"},
    {"code": "cuisse_g", "label": "Cuisse gauche"},
    {"code": "fesse", "label": "Fesse"},
    {"code": "oral", "label": "Voie orale"},
    {"code": "autre", "label": "Autre"},
]

VACCINATION_STRATEGIES = [
    {"code": "routine", "label": "Routine"},
    {"code": "campagne", "label": "Campagne"},
    {"code": "riposte", "label": "Riposte / Urgence"},
]

INJECTION_SITE_LABELS = {s["code"]: s["label"] for s in INJECTION_SITES}
STRATEGY_LABELS = {s["code"]: s["label"] for s in VACCINATION_STRATEGIES}
