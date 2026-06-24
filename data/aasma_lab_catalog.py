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

# (category_label, examination_name, price_gnf from tariff sheet or None)
_AASMA_EXAM_LINES: list[tuple[str, str, int | None]] = [
    # HEMATOLOGIE
    ("HEMATOLOGIE", "NFS / hémogramme complet", 120_000),
    ("HEMATOLOGIE", "Taux d'hémoglobine d'urgence", 120_000),
    ("HEMATOLOGIE", "Test d'Emmel", 50_000),
    ("HEMATOLOGIE", "Vitesse de sédimentation", 50_000),
    ("HEMATOLOGIE", "Frottis sanguin", 70_000),
    ("HEMATOLOGIE", "Groupe sanguin", 50_000),
    ("HEMATOLOGIE", "Test de Coombs", None),
    ("HEMATOLOGIE", "Électrophorèse d'hémoglobine", 250_000),
    ("HEMATOLOGIE", "Myélogramme", 300_000),
    # HEMOSTASE
    ("HEMOSTASE", "TCA / TCK", 150_000),
    ("HEMOSTASE", "TP / INR", 150_000),
    ("HEMOSTASE", "D-Dimères", 250_000),
    ("HEMOSTASE", "Fibrinogène", 200_000),
    ("HEMOSTASE", "TS / TC", None),
    # BIOCHIMIE
    ("BIOCHIMIE", "Glucose à jeun / glycémie", 50_000),
    ("BIOCHIMIE", "Glycémie d'urgence", 25_000),
    ("BIOCHIMIE", "Créatinine / créatininémie", 60_000),
    ("BIOCHIMIE", "Urée", 50_000),
    ("BIOCHIMIE", "Acide urique", 60_000),
    ("BIOCHIMIE", "ASAT", 80_000),
    ("BIOCHIMIE", "ALAT", 50_000),
    ("BIOCHIMIE", "Bilirubine totale", 350_000),
    ("BIOCHIMIE", "Bilirubine directe", 60_000),
    ("BIOCHIMIE", "Cholestérol total", 250_000),
    ("BIOCHIMIE", "Cholestérol HDL", 50_000),
    ("BIOCHIMIE", "Cholestérol LDL", 50_000),
    ("BIOCHIMIE", "Triglycérides", 300_000),
    ("BIOCHIMIE", "Protéines totales", 110_000),
    ("BIOCHIMIE", "Albuminémie", 85_000),
    ("BIOCHIMIE", "Albuminurie", 50_000),
    ("BIOCHIMIE", "Calcium / calcémie", 250_000),
    ("BIOCHIMIE", "Magnésium", 75_000),
    ("BIOCHIMIE", "Phosphore", 55_000),
    ("BIOCHIMIE", "Sodium", 55_000),
    ("BIOCHIMIE", "Potassium", 55_000),
    ("BIOCHIMIE", "Chlore", 50_000),
    ("BIOCHIMIE", "Ionogramme sanguin", 250_000),
    ("BIOCHIMIE", "Amylase", 80_000),
    ("BIOCHIMIE", "Lipase", 60_000),
    ("BIOCHIMIE", "Ferritine", 80_000),
    ("BIOCHIMIE", "Fer saturation", 95_000),
    ("BIOCHIMIE", "CRP", 50_000),
    ("BIOCHIMIE", "Glycorachie", 40_000),
    ("BIOCHIMIE", "Protéinurie", 50_000),
    ("BIOCHIMIE", "Microalbuminurie", 50_000),
    ("BIOCHIMIE", "Phosphatases alcalines", 80_000),
    ("BIOCHIMIE", "GGT", 80_000),
    ("BIOCHIMIE", "Bandelette urinaire", 60_000),
    ("BIOCHIMIE", "Électrophorèse des protéines", 250_000),
    ("BIOCHIMIE", "HbA1c", 250_000),
    # IMMUNO-SEROLOGIE
    ("IMMUNO-SEROLOGIE", "Sérologie rétrovirale VIH", 100_000),
    ("IMMUNO-SEROLOGIE", "Hépatite B AgHBs bandelette", 50_000),
    ("IMMUNO-SEROLOGIE", "AgHBe", 270_000),
    ("IMMUNO-SEROLOGIE", "Ac anti HBc Total", 300_000),
    ("IMMUNO-SEROLOGIE", "Hépatite C Ac anti VHC", 250_000),
    ("IMMUNO-SEROLOGIE", "Sérologie hépatite C", 120_000),
    ("IMMUNO-SEROLOGIE", "Syphilis", 50_000),
    ("IMMUNO-SEROLOGIE", "ASLO", 50_000),
    ("IMMUNO-SEROLOGIE", "Facteur rhumatoïde", 50_000),
    ("IMMUNO-SEROLOGIE", "Widal et Félix", 50_000),
    ("IMMUNO-SEROLOGIE", "Chlamydia", 60_000),
    ("IMMUNO-SEROLOGIE", "Rubéole", 300_000),
    ("IMMUNO-SEROLOGIE", "Toxoplasmose", 300_000),
    ("IMMUNO-SEROLOGIE", "RPR", 50_000),
    ("IMMUNO-SEROLOGIE", "TPHA", 50_000),
    ("IMMUNO-SEROLOGIE", "AgHBs", None),
    ("IMMUNO-SEROLOGIE", "AgHBs avec ELISA", None),
    ("IMMUNO-SEROLOGIE", "Ac anti-HBs quantitatif", None),
    ("IMMUNO-SEROLOGIE", "Ac anti-HBe", None),
    # BACTERIOLOGIE
    ("BACTERIOLOGIE", "ECBU simple", 100_000),
    ("BACTERIOLOGIE", "ECBU + Antibiogramme", 250_000),
    ("BACTERIOLOGIE", "ECBSV + Antibiogramme", 250_000),
    ("BACTERIOLOGIE", "ECB du pus + Antibiogramme", 250_000),
    ("BACTERIOLOGIE", "Hémoculture + antibiogramme", 250_000),
    ("BACTERIOLOGIE", "Coproculture", 250_000),
    ("BACTERIOLOGIE", "Analyse du liquide cérébro-spinal + antibiogramme", 250_000),
    # PARASITOLOGIE
    ("PARASITOLOGIE", "Goutte épaisse", 50_000),
    ("PARASITOLOGIE", "Recherche paludisme TDR", 25_000),
    ("PARASITOLOGIE", "Parasitologie des selles", None),
    ("PARASITOLOGIE", "Parasitologie des urines", 50_000),
    ("PARASITOLOGIE", "Recherche des microfilaires", 90_000),
    ("PARASITOLOGIE", "Examen microscopique direct des selles", 50_000),
    ("PARASITOLOGIE", "Examen mycologique", 175_000),
    # HORMONES
    ("HORMONES", "HCG urinaire", 50_000),
    ("HORMONES", "Test de grossesse", 55_000),
    ("HORMONES", "BHCG sanguin", None),
    ("HORMONES", "FSH", 300_000),
    ("HORMONES", "LH", 300_000),
    ("HORMONES", "TSH", 40_000),
    ("HORMONES", "Progestérone", 300_000),
    ("HORMONES", "Testostérone", 300_000),
    ("HORMONES", "Œstradiol", 300_000),
    ("HORMONES", "Prolactine", 300_000),
    ("HORMONES", "T3 Total", 300_000),
    ("HORMONES", "T4 Total", 300_000),
    ("HORMONES", "T3", None),
    ("HORMONES", "T4", None),
    # REPRODUCTION / FERTILITE
    ("REPRODUCTION / FERTILITE", "Spermogramme", None),
    ("REPRODUCTION / FERTILITE", "Spermocytogramme", None),
    ("REPRODUCTION / FERTILITE", "Spermo-culture", None),
    # MARQUEURS CANCEREUX
    ("MARQUEURS CANCEREUX", "PSA Total", 300_000),
    ("MARQUEURS CANCEREUX", "PSA Total et libre", None),
    ("MARQUEURS CANCEREUX", "CA 125", 300_000),
    ("MARQUEURS CANCEREUX", "CA 15-3", 300_000),
    ("MARQUEURS CANCEREUX", "CA 19-9", 75_000),
    ("MARQUEURS CANCEREUX", "AFP / Alpha foetoprotéine", 300_000),
    # AUTRES EXAMENS
    ("AUTRES EXAMENS", "H. Pylori dans le sang", 250_000),
    ("AUTRES EXAMENS", "H. Pylori dans les selles", 250_000),
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

    for idx, (category_label, name, price_gnf) in enumerate(_AASMA_EXAM_LINES):
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
            "price_gnf": price_gnf,
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
AASMA_TARIFF_COUNT = sum(1 for item in AASMA_LAB_CATALOG if item["price_gnf"] is not None)
