"""Tarifs laboratoire Clinique AASMA (GNF) — catalogue papier clinique."""

AASMA_CLINIC_ID = 17

AASMA_LAB_CATALOG = [
    {"code": "NFS", "name": "Numération formule sanguine (NFS)", "category": "hematology", "price_gnf": 35_000},
    {"code": "HB", "name": "Hémoglobine", "category": "hematology", "price_gnf": 15_000},
    {"code": "GS_RH", "name": "Groupage sanguin + Rhésus", "category": "hematology", "price_gnf": 20_000},
    {"code": "GLY", "name": "Glycémie", "category": "biochemistry", "price_gnf": 10_000},
    {"code": "GLY_PP", "name": "Glycémie post-prandiale", "category": "biochemistry", "price_gnf": 10_000},
    {"code": "UREE", "name": "Urée", "category": "biochemistry", "price_gnf": 15_000},
    {"code": "CREAT", "name": "Créatininémie", "category": "biochemistry", "price_gnf": 15_000},
    {"code": "ASAT", "name": "ASAT (TGO)", "category": "biochemistry", "price_gnf": 15_000},
    {"code": "ALAT", "name": "ALAT (TGP)", "category": "biochemistry", "price_gnf": 15_000},
    {"code": "BIL_T", "name": "Bilirubine totale", "category": "biochemistry", "price_gnf": 15_000},
    {"code": "CRP", "name": "CRP", "category": "immunology", "price_gnf": 25_000},
    {"code": "VS", "name": "Vitesse de sédimentation (VS)", "category": "hematology", "price_gnf": 10_000},
    {"code": "GE", "name": "Goutte épaisse (Paludisme)", "category": "parasitology", "price_gnf": 10_000},
    {"code": "TPHA", "name": "TPHA / Syphilis", "category": "serology", "price_gnf": 25_000},
    {"code": "HBSAG", "name": "Ag HBs (Hépatite B)", "category": "serology", "price_gnf": 30_000},
    {"code": "HIV", "name": "Test VIH", "category": "serology", "price_gnf": 30_000},
    {"code": "ECBU", "name": "ECBU", "category": "microbiology", "price_gnf": 20_000},
    {"code": "SPERM", "name": "Spermogramme", "category": "other", "price_gnf": 50_000},
    {"code": "BHCG", "name": "Beta-HCG (grossesse)", "category": "serology", "price_gnf": 25_000},
    {"code": "TSH", "name": "TSH", "category": "biochemistry", "price_gnf": 35_000},
    {"code": "CHOL", "name": "Cholestérol total", "category": "biochemistry", "price_gnf": 15_000},
    {"code": "TRIG", "name": "Triglycérides", "category": "biochemistry", "price_gnf": 15_000},
    {"code": "UREE_CREAT", "name": "Urée + Créatinine", "category": "biochemistry", "price_gnf": 25_000},
    {"code": "BILAN_HEP", "name": "Bilan hépatique (ASAT+ALAT+Bilirubine)", "category": "biochemistry", "price_gnf": 40_000},
    {"code": "BILAN_REN", "name": "Bilan rénal (Urée+Créatinine)", "category": "biochemistry", "price_gnf": 25_000},
]

AASMA_PRICE_BY_CODE = {t["code"]: t["price_gnf"] for t in AASMA_LAB_CATALOG}
