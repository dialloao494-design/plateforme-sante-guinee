"""Input validation helpers — Security Wave 1."""

from __future__ import annotations

import re

from fastapi import HTTPException, status
from pydantic import ConfigDict

# Shared config for sensitive request bodies (reject unknown fields).
FORBID_EXTRA = ConfigDict(extra="forbid")

_SQL_META = re.compile(
    r"(--|;/\*|\*/|\bunion\b\s+\bselect\b|\bdrop\b\s+\btable\b|\binsert\b\s+\binto\b|"
    r"\bdelete\b\s+\bfrom\b|\bupdate\b\s+\w+\s+\bset\b)",
    re.IGNORECASE,
)


def reject_suspicious_sql_input(value: str | None, *, field: str = "input") -> str | None:
    """
    Defense-in-depth for free-text search fields.

    ORM parameterization remains the primary SQLi control; this rejects obvious
    injection probes early with 400.
    """
    if value is None:
        return None
    cleaned = str(value).strip()
    if not cleaned:
        return cleaned
    if len(cleaned) > 200:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"{field} is too long",
        )
    if _SQL_META.search(cleaned):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field}",
        )
    return cleaned
