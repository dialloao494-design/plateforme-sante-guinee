"""Shared official clinic header for ReportLab PDF documents."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, Spacer, Table, TableStyle

from data.clinic_branding import (
    CLINIC_ADDRESS,
    CLINIC_COUNTRY,
    CLINIC_EMAIL,
    CLINIC_MINISTRY,
    CLINIC_MOTTO,
    CLINIC_PHONE,
    CLINIC_PRINT_NAME,
)
from services.pdf_fonts import ensure_clinic_fonts

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "aasma-clinic-logo.png"
GOLD = colors.HexColor("#C9A227")


def append_official_clinic_header(story: list, *, page_width: float, document_title: str | None = None) -> None:
    """Logo, official identity block, gold separator, optional document title."""
    font_reg, font_bold = ensure_clinic_fonts()
    if LOGO_PATH.is_file():
        img = Image(str(LOGO_PATH), width=38 * mm, height=38 * mm, kind="proportional")
        img.hAlign = "CENTER"
        story.append(img)
        story.append(Spacer(1, 3))

    base = getSampleStyleSheet()
    country = ParagraphStyle(
        "ClinicCountry",
        parent=base["Normal"],
        fontName=font_bold,
        fontSize=13,
        alignment=TA_CENTER,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=1,
    )
    motto = ParagraphStyle(
        "ClinicMotto",
        parent=base["Normal"],
        fontName=font_bold,
        fontSize=11,
        alignment=TA_CENTER,
        leading=13,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4,
    )
    ministry = ParagraphStyle(
        "ClinicMinistry",
        parent=base["Normal"],
        fontName=font_bold,
        fontSize=10,
        alignment=TA_CENTER,
        leading=12,
        textColor=colors.HexColor("#334155"),
    )
    name = ParagraphStyle(
        "ClinicName",
        parent=base["Normal"],
        fontName=font_bold,
        fontSize=12,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#134e4a"),
        leading=14,
        spaceAfter=2,
    )
    contact = ParagraphStyle(
        "ClinicContact", parent=base["Normal"], fontName=font_reg, fontSize=8, alignment=TA_CENTER, leading=10
    )
    title = ParagraphStyle(
        "DocTitle",
        parent=base["Heading1"],
        fontName=font_bold,
        fontSize=13,
        alignment=TA_CENTER,
        textColor=GOLD,
        spaceBefore=6,
        spaceAfter=8,
    )

    story.append(Paragraph(CLINIC_COUNTRY, country))
    story.append(Paragraph(CLINIC_MOTTO, motto))
    story.append(Paragraph(CLINIC_MINISTRY, ministry))
    story.append(Paragraph(CLINIC_PRINT_NAME, name))
    story.append(Paragraph(CLINIC_ADDRESS, contact))
    story.append(Paragraph(f"Tél. {CLINIC_PHONE} · {CLINIC_EMAIL}", contact))

    sep = Table([[""]], colWidths=[page_width], rowHeights=[2])
    sep.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1.2, GOLD)]))
    story.append(Spacer(1, 6))
    story.append(sep)
    story.append(Spacer(1, 8))

    if document_title:
        story.append(Paragraph(document_title, title))
