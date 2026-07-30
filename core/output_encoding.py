"""Output encoding helpers (XSS / PDF / HTML) — Security Wave 1."""

from __future__ import annotations

import html
import re
from xml.sax.saxutils import escape as xml_escape


_CTRL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def sanitize_text(value: object, *, max_length: int = 4000) -> str:
    """Strip control chars and truncate for safe display."""
    text = "" if value is None else str(value)
    text = _CTRL_RE.sub("", text)
    if len(text) > max_length:
        text = text[:max_length]
    return text


def escape_html(value: object) -> str:
    return html.escape(sanitize_text(value), quote=True)


def escape_xml(value: object) -> str:
    """Escape for ReportLab Paragraph / XML-ish markup."""
    return xml_escape(sanitize_text(value), {"'": "&apos;", '"': "&quot;"})


def escape_pdf_paragraph(value: object) -> str:
    """User-controlled strings embedded in ReportLab Paragraph markup."""
    return escape_xml(value)
