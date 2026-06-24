"""Catalogue laboratoire Clinique AASMA — grille tarifaire (4 photos) + formulaires papier."""

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

# Grille tarifaire AASMA — ordre exact des 4 photos (catégorie d'origine conservée)
_AASMA_TARIFF_LINES: list[tuple[str, str, int]] = [
    # Photo 1 (IMG_1178)
    ("IMMUNO-SEROLOGIE", "Ac anti HBc Total", 300_000),
    ("BIOCHIMIE", "Acide urique", 60_000),
    ("MARQUEURS CANCEREUX", "AFP- Alpha foetoprotéine", 300_000),
    ("IMMUNO-SEROLOGIE", "AgHBe", 270_000),
    ("BIOCHIMIE", "ALAT", 50_000),
    ("BIOCHIMIE", "Albuminémie", 85_000),
    ("BIOCHIMIE", "Albuminurie", 50_000),
    ("BIOCHIMIE", "Amylase (amylasémie)", 80_000),
    ("BACTERIOLOGIE", "Analyse du Liquide cérébro-spinal+ Antibiogramme", 250_000),
    ("IMMUNO-SEROLOGIE", "Antistreptolysin O (ASLO)", 50_000),
    ("BIOCHIMIE", "ASAT", 50_000),
    ("BIOCHIMIE", "Bandelette Urinaire", 80_000),
    ("BIOCHIMIE", "Bilirubine Directe", 60_000),
    ("BIOCHIMIE", "Bilirubine totale", 60_000),
    ("MARQUEURS CANCEREUX", "CA 125", 350_000),
    ("MARQUEURS CANCEREUX", "CA 15-3", 300_000),
    ("MARQUEURS CANCEREUX", "CA 19-9", 300_000),
    ("BIOCHIMIE", "Calcium (calcemie)", 75_000),
    ("IMMUNO-SEROLOGIE", "Chlamydia", 250_000),
    ("BIOCHIMIE", "Chloré", 60_000),
    ("BIOCHIMIE", "Cholestérol HDL", 50_000),
    ("BIOCHIMIE", "Cholestérol LDL", 50_000),
    ("BIOCHIMIE", "Cholestérol total", 50_000),
    ("BACTERIOLOGIE", "Coproculture", 250_000),
    # Photo 2 (IMG_1180)
    ("BIOCHIMIE", "Créatinine (créatinémie)", 60_000),
    ("HEMOSTASE", "D-Dimères", 300_000),
    ("BACTERIOLOGIE", "ECB du pus + Antibiogramme", 250_000),
    ("BACTERIOLOGIE", "ECBSV+Antibiogramme", 250_000),
    ("BACTERIOLOGIE", "ECBU + Antibiogramme", 250_000),
    ("BACTERIOLOGIE", "ECBU simple", 100_000),
    ("BIOCHIMIE", "Electrophorèse des proteines", 250_000),
    ("HEMATOLOGIE", "Electrophorèse d'hémoglobine", 250_000),
    ("PARASITOLOGIE", "Examen microscopique direct des selles", 50_000),
    ("PARASITOLOGIE", "Examen mycologique (Recherche de champignons)", 175_000),
    ("IMMUNO-SEROLOGIE", "Facteur Rhumatoïde", 50_000),
    ("BIOCHIMIE", "Fer; saturation", 95_000),
    ("BIOCHIMIE", "Ferritine", 80_000),
    ("HEMOSTASE", "Fibrinogène", 200_000),
    ("HEMATOLOGIE", "Frottis sanguin", 70_000),
    ("HORMONES", "FSH", 300_000),
    ("BIOCHIMIE", "Gamma-Glutamyl Transférase (GGT)", 80_000),
    ("BIOCHIMIE", "Glucose à jeun (glycémie) - (Automate)", 50_000),
    ("BIOCHIMIE", "Glycémie d'urgence - (Hémocu)", 25_000),
    ("BIOCHIMIE", "Glycorachie", 40_000),
    ("PARASITOLOGIE", "Goutte épaisse (Dp)", 50_000),
    ("HEMATOLOGIE", "Groupe sanguin", 50_000),
    ("AUTRES EXAMENS", "H.Pylori dans le sang", 250_000),
    ("AUTRES EXAMENS", "H.Pylori dans les selles", 250_000),
    ("AUTRES EXAMENS", "HCG urinaire", 50_000),
    # Photo 3 (IMG_1181)
    ("BACTERIOLOGIE", "Hémoculture (incl, antibiogramme)", 250_000),
    ("AUTRES EXAMENS", "Hémoglobine glyquée A1c (Hb A1c)", 250_000),
    ("AUTRES EXAMENS", "Hépatite B (AgHBs) bandelette", 50_000),
    ("AUTRES EXAMENS", "Hépatite C (Ac anti VHC)", 250_000),
    ("BIOCHIMIE", "Ionogramme sanguin", 250_000),
    ("HORMONES", "LH", 300_000),
    ("BIOCHIMIE", "Lipase (Lipasemie)", 60_000),
    ("BIOCHIMIE", "Magnésium (Magnesemie)", 75_000),
    ("BIOCHIMIE", "Microalbuminurie", 50_000),
    ("HEMATOLOGIE", "Myélogramme (Médulogramme)", 300_000),
    ("HEMATOLOGIE", "NFS (hemogramme complet)", 120_000),
    ("HORMONES", "Oestradiol", 300_000),
    ("PARASITOLOGIE", "Parasitologies des urines", 50_000),
    ("BIOCHIMIE", "Phosphatases alcalines", 80_000),
    ("BIOCHIMIE", "Phosphore (phosphorémie)", 55_000),
    ("BIOCHIMIE", "Potassium (kaliémie)", 55_000),
    ("HORMONES", "Progestérone", 300_000),
    ("HORMONES", "Prolactine", 300_000),
    ("BIOCHIMIE", "Protéine C-réactive (CRP)", 50_000),
    ("BIOCHIMIE", "Protéines totales (protides plasmatiques)", 110_000),
    ("BIOCHIMIE", "Protéinurie", 50_000),
    ("MARQUEURS CANCEREUX", "PSA Total", 300_000),
    ("PARASITOLOGIE", "Recherche des Microfilaires", 90_000),
    ("PARASITOLOGIE", "Recherche paludisme -TDR", 25_000),
    # Photo 4 (IMG_1182)
    ("IMMUNO-SEROLOGIE", "RPR", 50_000),
    ("IMMUNO-SEROLOGIE", "Rubéole", 300_000),
    ("IMMUNO-SEROLOGIE", "Sérologie hépatite C", 120_000),
    ("IMMUNO-SEROLOGIE", "Sérologie rétrovirale VIH", 100_000),
    ("BIOCHIMIE", "Sodium", 55_000),
    ("IMMUNO-SEROLOGIE", "Syphilis", 50_000),
    ("HORMONES", "T3 Total", 300_000),
    ("HORMONES", "T4 Total", 300_000),
    ("HEMATOLOGIE", "Taux d'hémoglobine d'urgence (hemmograme)", 120_000),
    ("HEMOSTASE", "TCA; TCK (Temps de céphaline kaolin)", 150_000),
    ("HORMONES", "Test de grossesse", 55_000),
    ("HEMATOLOGIE", "Test d'Emmel", 50_000),
    ("HORMONES", "Testostérone", 300_000),
    ("HORMONES", "Testostérone", 300_000),
    ("IMMUNO-SEROLOGIE", "Toxoplasmose", 300_000),
    ("HEMOSTASE", "TP; INR (Temps de prothrombine; International Norm", 150_000),
    ("IMMUNO-SEROLOGIE", "TPHA", 50_000),
    ("BIOCHIMIE", "Triglycérides", 50_000),
    ("HORMONES", "TSH", 300_000),
    ("BIOCHIMIE", "Urée", 40_000),
    ("HEMATOLOGIE", "Vitesse de sédimentation", 50_000),
    ("IMMUNO-SEROLOGIE", "Widal et Félix", 50_000),
]

# Examens des formulaires papier AASMA absents de la grille tarifaire (sans prix inventé)
_AASMA_FORM_LINES: list[tuple[str, str]] = [
    ("HEMATOLOGIE", "Test de Coombs"),
    ("HEMOSTASE", "TS / TC"),
    ("IMMUNO-SEROLOGIE", "SRV (VIH)"),
    ("IMMUNO-SEROLOGIE", "AgHBs"),
    ("IMMUNO-SEROLOGIE", "AgHBs avec ELISA"),
    ("IMMUNO-SEROLOGIE", "Ac anti-HBs quantitatif"),
    ("IMMUNO-SEROLOGIE", "Ac anti-HCV"),
    ("IMMUNO-SEROLOGIE", "Ac anti-HBe"),
    ("IMMUNO-SEROLOGIE", "CRP"),
    ("IMMUNO-SEROLOGIE", "Syphilis (VDRL/TPHA)"),
    ("HORMONES", "BHCG urinaire"),
    ("HORMONES", "BHCG sanguin"),
    ("HORMONES", "T3"),
    ("HORMONES", "T4"),
    ("REPRODUCTION / FERTILITE", "Spermogramme"),
    ("REPRODUCTION / FERTILITE", "Spermocytogramme"),
    ("REPRODUCTION / FERTILITE", "Spermo-culture"),
    ("MARQUEURS CANCEREUX", "PSA Total et libre"),
    ("PARASITOLOGIE", "Parasitologie des selles"),
    ("AUTRES EXAMENS", "H. Pylori dans le sang"),
    ("AUTRES EXAMENS", "H. Pylori dans les selles"),
    ("AUTRES EXAMENS", "Recherche paludisme TDR"),
    ("AUTRES EXAMENS", "Recherche des microfilaires"),
    ("AUTRES EXAMENS", "Créatinine"),
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
    idx = 0

    for category_label, name, price_gnf in _AASMA_TARIFF_LINES:
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
            "tariff_sheet": True,
        }
        flat.append(entry)
        by_category.setdefault(display_label, []).append(entry)
        idx += 1

    for category_label, name in _AASMA_FORM_LINES:
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
            "tariff_sheet": False,
        }
        flat.append(entry)
        by_category.setdefault(display_label, []).append(entry)
        idx += 1

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
AASMA_TARIFF_COUNT = len(_AASMA_TARIFF_LINES)
