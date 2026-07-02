"""Official AASMA laboratory report templates — match clinic paper forms."""

from __future__ import annotations

CLINIC_LAB_FOOTER_ADDRESS = (
    "CHFMP-Polyclinique AASMA sis à Kobaya chinoiya, "
    "sur la colline entre la Pharmacie Dara et les écoles MOLASY"
)
CLINIC_LAB_FOOTER_CONTACT = "Téléphone : 613 04 94 48    Email : contactpolycliniqueaasma@gmail.com"

HEMOGRAM_TITLE = "Hémogramme (Mindray BC-10)"
HEMOGRAM_NOTE = "NB : L'hémogramme varie en fonction de l'âge, du sexe et des paramètres physiologiques"

HEMOGRAM_ROWS = [
    {"parameter": "GB", "unit": "10^9/L", "ref_child": "4.0 – 12.0", "ref_male": "4.0 – 10.0", "ref_female": "4.0 – 10.0"},
    {"parameter": "Lymph", "unit": "10^9/L", "ref_child": "0.8 – 7.0", "ref_male": "0.8 – 4.0", "ref_female": "0.8 – 4.0"},
    {"parameter": "Mid", "unit": "10^9/L", "ref_child": "0.1 – 1.0", "ref_male": "0.1 – 1.5", "ref_female": "0.1 – 1.5"},
    {"parameter": "Gran", "unit": "10^9/L", "ref_child": "2.0 – 6.0", "ref_male": "2.0 – 7.0", "ref_female": "2.0 – 7.0"},
    {"parameter": "Lymph%", "unit": "%", "ref_child": "20.0 – 50.0", "ref_male": "0.200 – 0.400", "ref_female": "0.200 – 0.400"},
    {"parameter": "Mid%", "unit": "%", "ref_child": "0.500 – 10.0", "ref_male": "0.030 – 0.150", "ref_female": "0.030 – 0.150"},
    {"parameter": "Gran%", "unit": "%", "ref_child": "20.0 – 70.0", "ref_male": "0.500 – 0.700", "ref_female": "0.500 – 0.700"},
    {"parameter": "RBC", "unit": "10^12/L", "ref_child": "3.50 – 5.20", "ref_male": "4.00 – 5.50", "ref_female": "3.50 – 5.00"},
    {"parameter": "HGB", "unit": "g/L", "ref_child": "115 – 160", "ref_male": "120 – 160", "ref_female": "110 – 150"},
    {"parameter": "HCT", "unit": "L/L", "ref_child": "0.350 – 0.490", "ref_male": "0.400 – 0.540", "ref_female": "0.370 – 0.470"},
    {"parameter": "MCV", "unit": "fL", "ref_child": "80.0 – 100.0", "ref_male": "80.0 – 100.0", "ref_female": "80.0 – 100.0"},
    {"parameter": "MCH", "unit": "pg", "ref_child": "27.0 – 34.0", "ref_male": "27.0 – 34.0", "ref_female": "27.0 – 34.0"},
    {"parameter": "MCHC", "unit": "g/L", "ref_child": "310 – 360", "ref_male": "320 – 360", "ref_female": "320 – 360"},
    {"parameter": "RDW-CV", "unit": "", "ref_child": "0.110 – 0.160", "ref_male": "0.110 – 0.160", "ref_female": "0.110 – 0.160"},
    {"parameter": "RDW-SD", "unit": "fL", "ref_child": "35.0 – 56.0", "ref_male": "35.0 – 56.0", "ref_female": "35.0 – 56.0"},
    {"parameter": "PLT", "unit": "10^9/L", "ref_child": "150 – 500", "ref_male": "100 – 300", "ref_female": "100 – 300"},
    {"parameter": "MPV", "unit": "fL", "ref_child": "6.0 – 13.0", "ref_male": "6.5 – 12.0", "ref_female": "6.5 – 12.0"},
    {"parameter": "PDW", "unit": "", "ref_child": "10.0 – 18.0", "ref_male": "15.0 – 17.0", "ref_female": "15.0 – 17.0"},
    {"parameter": "PCT", "unit": "mL/L", "ref_child": "1.08 – 2.82", "ref_male": "1.08 – 2.82", "ref_female": "1.08 – 2.82"},
    {"parameter": "P-LCR", "unit": "", "ref_child": "0.110 – 0.450", "ref_male": "0.110 – 0.450", "ref_female": "0.110 – 0.450"},
]

BU_TITLE = "Biochimie des urines (BU)"
BU_ROWS = [
    {"parameter": "Leucocytes", "reference": "Négatif"},
    {"parameter": "Nitrite", "reference": "Négatif"},
    {"parameter": "PH", "reference": "5.0-8.5"},
    {"parameter": "Urobilinogène", "reference": "Normal"},
    {"parameter": "Bilirubine", "reference": "Négatif"},
    {"parameter": "Sang", "reference": "Négatif"},
    {"parameter": "Densité", "reference": "1.005-1.030"},
    {"parameter": "Protéine", "reference": "Négatif"},
    {"parameter": "Glucose", "reference": "Négatif"},
    {"parameter": "Cétone", "reference": "Négatif"},
]

ECBU_TITLE = "Examen Cytobactériologique des Urines (ECBU)"
ECBU_MACRO = "Aspect macroscopique : urine jaune clair, culot léger"
ECBU_ROWS = [
    {"parameter": "Leucocytes", "unit": "mm³", "reference": "<10"},
    {"parameter": "Hématies", "unit": "mm³", "reference": "<10"},
    {"parameter": "Cellules épithéliales", "unit": "", "reference": "0-5"},
    {"parameter": "Cylindres", "unit": "", "reference": "Absents"},
    {"parameter": "Cristaux", "unit": "", "reference": "Absents ou rares"},
    {"parameter": "Levures", "unit": "", "reference": "Absentes"},
    {"parameter": "Parasites", "unit": "", "reference": "Absentes"},
    {"parameter": "Gram", "unit": "", "reference": "Absent"},
    {"parameter": "Culture/identification", "unit": "", "reference": ""},
]

TEMPLATES = {
    "hemogram": {
        "id": "hemogram",
        "title": HEMOGRAM_TITLE,
        "type": "hemogram",
        "note": HEMOGRAM_NOTE,
        "rows": HEMOGRAM_ROWS,
        "keywords": ["hémogramme", "hemogramme", "nfs", "mindray", "bc-10", "bc10"],
    },
    "bu": {
        "id": "bu",
        "title": BU_TITLE,
        "type": "bu",
        "rows": BU_ROWS,
        "keywords": ["biochimie des urines", "biochimie urinaire", "bu ", " bandelette"],
    },
    "ecbu": {
        "id": "ecbu",
        "title": ECBU_TITLE,
        "type": "ecbu",
        "macro": ECBU_MACRO,
        "rows": ECBU_ROWS,
        "keywords": ["ecbu", "cytobact", "cytobactériologique", "cytobacteriologique"],
    },
}


def detect_template_id(test_name: str) -> str | None:
    name = (test_name or "").lower()
    for tid, tpl in TEMPLATES.items():
        if any(kw in name for kw in tpl["keywords"]):
            return tid
    return None
