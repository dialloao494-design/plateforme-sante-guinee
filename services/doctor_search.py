"""
Flexible doctor directory search (titles stripped, multi-token, partial match).
"""

from __future__ import annotations

import re

from sqlalchemy import String, and_, cast, func, or_
from sqlalchemy.orm import Query

from models.doctor import Doctor


# French / common shorthands → substring matched against Doctor.specialty (ilike)
SPECIALTY_HINTS: dict[str, str] = {
    "pédiatre": "pédiat",
    "pediatre": "pédiat",
    "pédiatrie": "pédiat",
    "généraliste": "médecine générale",
    "generaliste": "médecine générale",
    "cardio": "cardio",
    "cardiologue": "cardio",
    "dermato": "dermato",
    "dermatologue": "dermato",
    "gynéco": "gyné",
    "gyneco": "gyné",
    "orl": "orl",
}


def normalize_doctor_search_query(raw: str | None) -> str:
    if not raw:
        return ""
    s = str(raw).strip().lower()
    s = re.sub(r"\s+", " ", s)
    # Strip leading honorifics (repeat to handle "dr dr amina")
    for _ in range(3):
        s2 = re.sub(r"^(dr\.?|docteur\.?|doctor\.?)\s+", "", s, flags=re.IGNORECASE)
        if s2 == s:
            break
        s = s2
    s = re.sub(r"\s+(dr\.?|docteur\.?|doctor\.?)\s+", " ", s, flags=re.IGNORECASE)
    return s.strip()


def _full_name_expr():
    return func.trim(cast(func.concat(Doctor.first_name, " ", Doctor.last_name), String))


def apply_doctor_search_filter(q: Query, search: str | None) -> Query:
    """Narrow a Doctor query with flexible name / specialty / city matching."""
    norm = normalize_doctor_search_query(search)
    if not norm:
        return q
    tokens = [t for t in norm.split(" ") if t]
    if not tokens:
        return q

    def clauses_for_token(tok: str):
        pattern = f"%{tok}%"
        full = _full_name_expr()
        parts = [
            Doctor.first_name.ilike(pattern),
            Doctor.last_name.ilike(pattern),
            Doctor.specialty.ilike(pattern),
            Doctor.city.ilike(pattern),
            full.ilike(pattern),
        ]
        hint = SPECIALTY_HINTS.get(tok)
        if hint:
            parts.append(Doctor.specialty.ilike(f"%{hint}%"))
        return or_(*parts)

    return q.filter(and_(*[clauses_for_token(t) for t in tokens]))
