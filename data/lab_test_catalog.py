"""Standard laboratory test catalog for Guinean primary care."""

LAB_TEST_CATALOG = [
    {"code": "NFS", "name": "Numération formule sanguine (CBC)", "category": "hematology"},
    {"code": "HB", "name": "Hémoglobine", "category": "hematology"},
    {"code": "GLY", "name": "Glycémie", "category": "biochemistry"},
    {"code": "ECBU", "name": "ECBU", "category": "microbiology"},
    {"code": "GE", "name": "Goutte épaisse (Paludisme)", "category": "parasitology"},
    {"code": "TPHA", "name": "TPHA / Syphilis", "category": "serology"},
    {"code": "HBSAG", "name": "Ag HBs (Hépatite B)", "category": "serology"},
    {"code": "HIV", "name": "VIH", "category": "serology"},
    {"code": "GS_RH", "name": "Groupage sanguin + Rhésus", "category": "hematology"},
    {"code": "CRP", "name": "CRP", "category": "immunology"},
    {"code": "CREAT", "name": "Créatininémie", "category": "biochemistry"},
    {"code": "UREE", "name": "Urée", "category": "biochemistry"},
    {"code": "CUSTOM", "name": "Autre examen", "category": "other"},
]

LAB_CATEGORIES = {
    "hematology": "Hématologie",
    "biochemistry": "Biochimie",
    "microbiology": "Microbiologie",
    "parasitology": "Parasitologie",
    "serology": "Sérologie",
    "immunology": "Immunologie",
    "other": "Autre",
}
