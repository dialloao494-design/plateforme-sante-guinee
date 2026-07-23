"""Unicode-safe A4 PDF for short clinical documents (discharge, imaging, reports)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer

from data.clinic_branding import CLINIC_PRINT_NAME
from services.pdf_fonts import ensure_clinic_fonts

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "aasma-clinic-logo.png"


def build_unicode_simple_pdf(title: str, lines: list[str]) -> bytes:
    """Build an A4 PDF with clinic branding and French-capable fonts."""
    font_reg, font_bold = ensure_clinic_fonts()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=16 * mm,
    )
    base = getSampleStyleSheet()
    styles = {
        "clinic": ParagraphStyle(
            "SimpleClinic",
            parent=base["Normal"],
            fontName=font_bold,
            fontSize=11,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f766e"),
            spaceAfter=2 * mm,
        ),
        "title": ParagraphStyle(
            "SimpleTitle",
            parent=base["Heading1"],
            fontName=font_bold,
            fontSize=13,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#134e4a"),
            spaceAfter=6 * mm,
        ),
        "body": ParagraphStyle(
            "SimpleBody",
            parent=base["Normal"],
            fontName=font_reg,
            fontSize=10,
            alignment=TA_LEFT,
            leading=14,
            spaceAfter=1.5 * mm,
        ),
    }

    story = []
    if LOGO_PATH.is_file():
        try:
            story.append(Image(str(LOGO_PATH), width=42 * mm, height=28 * mm, kind="proportional"))
            story.append(Spacer(1, 2 * mm))
        except Exception:
            pass
    story.append(Paragraph(_esc(CLINIC_PRINT_NAME), styles["clinic"]))
    story.append(Paragraph(_esc(title), styles["title"]))
    for line in lines:
        text = (line or "").strip()
        if not text:
            story.append(Spacer(1, 2 * mm))
            continue
        story.append(Paragraph(_esc(text), styles["body"]))

    doc.build(story)
    return buf.getvalue()


def _esc(value: str) -> str:
    return (
        (value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
