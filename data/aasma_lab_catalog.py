"""Catalogue laboratoire Clinique AASMA — formulaires et grilles tarifaires papier."""

from __future__ import annotations

import re
import unicodedata

AASMA_CLINIC_ID = 17

_CATEGORY_PREFIX = {
    "HEMATOLOGIE": "HEM",
    "HEMOSTASE": "HEMO",
    "BIOCHIMIE": "BIO",
    "IMMUNO-SEROLOGIE": "IMM",
    "BACTERIOLOGIE": "BAC",
    "PARASITOLOGIE": "PAR",
    "HORMONES": "HOR",
    "REPRODUCTION / FERTILITE": "REP",
    "MARQUEURS CANCEREUX": "MAR",
    "AUTRES EXAMENS": "AUT",
}

_CATEGORY_DISPLAY = {
    "HEMATOLOGIE": "Hématologie",
    "HEMOSTASE": "Hémostase",
    "BIOCHIMIE": "Biochimie",
    "IMMUNO-SEROLOGIE": "Immuno-Sérologie",
    "BACTERIOLOGIE": "Bactériologie",
    "PARASITOLOGIE": "Parasitologie",
    "HORMONES": "Hormones",
    "REPRODUCTION / FERTILITE": "Reproduction/Fertilité",
    "MARQUEURS CANCEREUX": "Marqueurs Cancéreux",
    "AUTRES EXAMENS": "Autres examens",
}

# (category_label, examination_name) — ordre des formulaires AASMA
_AASMA_EXAM_LINES: list[tuple[str, str]] = [
    # HEMATOLOGIE
    ("HEMATOLOGIE", "NFS"),
    ("HEMATOLOGIE", "Taux d'hémoglobine d'urgence"),
    ("HEMATOLOGIE", "Test d'Emmel"),
    ("HEMATOLOGIE", "Vitesse de sédimentation (VS)"),
    ("HEMATOLOGIE", "Frottis sanguin"),
    ("HEMATOLOGIE", "Groupe sanguin"),
    ("HEMATOLOGIE", "Test de Coombs"),
    ("HEMATOLOGIE", "Electrophorèse d'hémoglobine"),
    ("HEMATOLOGIE", "Myélogramme"),
    # HEMOSTASE
    ("HEMOSTASE", "TCK / TCA"),
    ("HEMOSTASE", "TP / INR"),
    ("HEMOSTASE", "D-Dimères"),
    ("HEMOSTASE", "Fibrinogène"),
    ("HEMOSTASE", "TS / TC"),
    # BIOCHIMIE
    ("BIOCHIMIE", "Glycémie"),
    ("BIOCHIMIE", "Créatininémie"),
    ("BIOCHIMIE", "Urée"),
    ("BIOCHIMIE", "Acide urique"),
    ("BIOCHIMIE", "ASAT"),
    ("BIOCHIMIE", "ALAT"),
    ("BIOCHIMIE", "Bilirubine totale"),
    ("BIOCHIMIE", "Bilirubine directe"),
    ("BIOCHIMIE", "Cholestérol total"),
    ("BIOCHIMIE", "Cholestérol HDL"),
    ("BIOCHIMIE", "Cholestérol LDL"),
    ("BIOCHIMIE", "Triglycérides"),
    ("BIOCHIMIE", "Protéines totales"),
    ("BIOCHIMIE", "Albuminémie"),
    ("BIOCHIMIE", "Albuminurie"),
    ("BIOCHIMIE", "Calcémie"),
    ("BIOCHIMIE", "Magnésémie"),
    ("BIOCHIMIE", "Phosphorémie"),
    ("BIOCHIMIE", "Sodium"),
    ("BIOCHIMIE", "Potassium"),
    ("BIOCHIMIE", "Chlore"),
    ("BIOCHIMIE", "Ionogramme sanguin"),
    ("BIOCHIMIE", "Amylase"),
    ("BIOCHIMIE", "Lipase"),
    ("BIOCHIMIE", "Ferritine"),
    ("BIOCHIMIE", "Fer saturation"),
    ("BIOCHIMIE", "CRP"),
    ("BIOCHIMIE", "Glycorachie"),
    ("BIOCHIMIE", "Protéinurie"),
    ("BIOCHIMIE", "Microalbuminurie"),
    ("BIOCHIMIE", "Phosphatases alcalines"),
    ("BIOCHIMIE", "GGT"),
    # IMMUNO-SEROLOGIE
    ("IMMUNO-SEROLOGIE", "SRV (VIH)"),
    ("IMMUNO-SEROLOGIE", "AgHBs"),
    ("IMMUNO-SEROLOGIE", "AgHBe"),
    ("IMMUNO-SEROLOGIE", "AgHBs avec ELISA"),
    ("IMMUNO-SEROLOGIE", "Ac anti-HBs quantitatif"),
    ("IMMUNO-SEROLOGIE", "Ac anti-HBc"),
    ("IMMUNO-SEROLOGIE", "Ac anti-HCV"),
    ("IMMUNO-SEROLOGIE", "Ac anti-HBe"),
    ("IMMUNO-SEROLOGIE", "Sérologie Hépatite C"),
    ("IMMUNO-SEROLOGIE", "Syphilis (VDRL/TPHA)"),
    ("IMMUNO-SEROLOGIE", "ASLO"),
    ("IMMUNO-SEROLOGIE", "Facteur rhumatoïde"),
    ("IMMUNO-SEROLOGIE", "CRP"),
    ("IMMUNO-SEROLOGIE", "Widal et Félix"),
    ("IMMUNO-SEROLOGIE", "Chlamydia"),
    ("IMMUNO-SEROLOGIE", "Rubéole"),
    ("IMMUNO-SEROLOGIE", "Toxoplasmose"),
    ("IMMUNO-SEROLOGIE", "RPR"),
    ("IMMUNO-SEROLOGIE", "TPHA"),
    ("IMMUNO-SEROLOGIE", "Sérologie rétrovirale VIH"),
    # BACTERIOLOGIE
    ("BACTERIOLOGIE", "ECBU"),
    ("BACTERIOLOGIE", "ECBU + Antibiogramme"),
    ("BACTERIOLOGIE", "ECBSV + Antibiogramme"),
    ("BACTERIOLOGIE", "ECB du pus + Antibiogramme"),
    ("BACTERIOLOGIE", "Hémoculture"),
    ("BACTERIOLOGIE", "Coproculture"),
    ("BACTERIOLOGIE", "Analyse du liquide céphalo-rachidien + antibiogramme"),
    # PARASITOLOGIE
    ("PARASITOLOGIE", "Goutte épaisse (GE)"),
    ("PARASITOLOGIE", "TDR Paludisme"),
    ("PARASITOLOGIE", "Parasitologie des selles"),
    ("PARASITOLOGIE", "Parasitologie des urines"),
    ("PARASITOLOGIE", "Recherche des microfilaires"),
    ("PARASITOLOGIE", "Examen microscopique direct des selles"),
    ("PARASITOLOGIE", "Examen mycologique (champignons)"),
    # HORMONES
    ("HORMONES", "BHCG urinaire"),
    ("HORMONES", "BHCG sanguin"),
    ("HORMONES", "FSH"),
    ("HORMONES", "LH"),
    ("HORMONES", "TSH"),
    ("HORMONES", "Progestérone"),
    ("HORMONES", "Testostérone"),
    ("HORMONES", "Oestradiol"),
    ("HORMONES", "Prolactine"),
    ("HORMONES", "T3"),
    ("HORMONES", "T4"),
    ("HORMONES", "T3 Total"),
    ("HORMONES", "T4 Total"),
    # REPRODUCTION / FERTILITE
    ("REPRODUCTION / FERTILITE", "Spermogramme"),
    ("REPRODUCTION / FERTILITE", "Spermocytogramme"),
    ("REPRODUCTION / FERTILITE", "Spermo-culture"),
    # MARQUEURS CANCEREUX
    ("MARQUEURS CANCEREUX", "PSA Total"),
    ("MARQUEURS CANCEREUX", "PSA Total et libre"),
    ("MARQUEURS CANCEREUX", "CA125"),
    ("MARQUEURS CANCEREUX", "CA15-3"),
    ("MARQUEURS CANCEREUX", "CA19-9"),
    ("MARQUEURS CANCEREUX", "AFP (Alpha Foetoprotéine)"),
    # AUTRES EXAMENS
    ("AUTRES EXAMENS", "H. Pylori dans le sang"),
    ("AUTRES EXAMENS", "H. Pylori dans les selles"),
    ("AUTRES EXAMENS", "HCG urinaire"),
    ("AUTRES EXAMENS", "Recherche paludisme TDR"),
    ("AUTRES EXAMENS", "Recherche des microfilaires"),
    ("AUTRES EXAMENS", "Créatinine"),
    ("AUTRES EXAMENS", "HbA1c"),
    ("AUTRES EXAMENS", "Hépatite B bandelette"),
    ("AUTRES EXAMENS", "Hépatite C (Ac anti VHC)"),
    ("AUTRES EXAMENS", "Protéines plasmatiques"),
    ("AUTRES EXAMENS", "Calcium"),
    ("AUTRES EXAMENS", "Magnésium"),
    ("AUTRES EXAMENS", "Phosphore"),
    ("AUTRES EXAMENS", "Potassium"),
    ("AUTRES EXAMENS", "Sodium"),
]


def _slugify(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_name.lower()).strip("_")
    return slug or "exam"


def _build_catalog() -> tuple[list[dict], list[dict]]:
    flat: list[dict] = []
    categories: list[dict] = []
    seen_codes: dict[str, int] = {}
    by_category: dict[str, list[dict]] = {}

    for idx, (category_label, name) in enumerate(_AASMA_EXAM_LINES):
        prefix = _CATEGORY_PREFIX[category_label]
        base = f"{prefix}_{_slugify(name)}"
        count = seen_codes.get(base, 0)
        seen_codes[base] = count + 1
        code = base if count == 0 else f"{base}_{count + 1}"
        category_key = _slugify(category_label)
        display_label = _CATEGORY_DISPLAY.get(category_label, category_label)
        entry = {
            "code": code,
            "name": name,
            "category": category_key,
            "category_label": display_label,
            "price_gnf": None,
            "sort_order": idx,
        }
        flat.append(entry)
        by_category.setdefault(display_label, []).append(entry)

    for category_label, tests in by_category.items():
        categories.append(
            {
                "key": _slugify(category_label),
                "label": category_label,
                "tests": tests,
            }
        )

    return flat, categories


AASMA_LAB_CATALOG, AASMA_LAB_CATEGORIES = _build_catalog()
AASMA_CATEGORY_COUNT = len(AASMA_LAB_CATEGORIES)
AASMA_EXAM_COUNT = len(AASMA_LAB_CATALOG)
