"""Professional A4 hospital invoice PDF (ReportLab)."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from data.clinic_branding import CLINIC_FOOTER_LINE, CLINIC_PRINT_NAME
from services.clinic_print_header import append_official_clinic_header
from services.pdf_fonts import ensure_clinic_fonts

METHOD_LABELS = {
    "cash": "Espèces",
    "orange_money": "Orange Money",
    "bank_transfer": "Virement bancaire",
    "card": "Carte bancaire",
    "insurance": "Assurance",
}


def _gnf(amount: int) -> str:
    return f"{int(amount):,} GNF".replace(",", " ")


def _styles():
    font_reg, font_bold = ensure_clinic_fonts()
    base = getSampleStyleSheet()
    return {
        "font_reg": font_reg,
        "font_bold": font_bold,
        "title": ParagraphStyle(
            "InvTitle",
            parent=base["Heading1"],
            fontName=font_bold,
            fontSize=14,
            alignment=TA_CENTER,
            spaceAfter=4,
            textColor=colors.HexColor("#0f766e"),
        ),
        "clinic": ParagraphStyle(
            "ClinicName",
            parent=base["Normal"],
            fontName=font_bold,
            fontSize=11,
            alignment=TA_CENTER,
            spaceAfter=2,
            textColor=colors.HexColor("#134e4a"),
        ),
        "meta": ParagraphStyle(
            "Meta",
            parent=base["Normal"],
            fontName=font_reg,
            fontSize=9,
            leading=12,
        ),
        "meta_right": ParagraphStyle(
            "MetaR",
            parent=base["Normal"],
            fontName=font_reg,
            fontSize=9,
            alignment=TA_RIGHT,
            leading=12,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=base["Normal"],
            fontName=font_bold,
            fontSize=10,
            spaceBefore=8,
            spaceAfter=4,
            textColor=colors.HexColor("#0f766e"),
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=base["Normal"],
            fontName=font_reg,
            fontSize=9,
            leading=11,
        ),
        "cell_right": ParagraphStyle(
            "CellR",
            parent=base["Normal"],
            fontName=font_reg,
            fontSize=9,
            alignment=TA_RIGHT,
            leading=11,
        ),
        "footer": ParagraphStyle(
            "Footer",
            parent=base["Normal"],
            fontName=font_reg,
            fontSize=8,
            textColor=colors.grey,
            leading=10,
        ),
    }


def build_hospital_invoice_pdf(
    *,
    invoice_number: str,
    patient_name: str,
    patient_file_number: str = "",
    items: list[dict],
    subtotal: int,
    exemption_percent: float = 0,
    exemption_amount: int = 0,
    total: int,
    paid: int,
    payment_details: list[dict] | None = None,
    printed_by: str = "",
    printed_date: str = "",
    printed_time: str = "",
    document_title: str = "FACTURE",
) -> bytes:
    remaining = max(0, int(total) - int(paid))
    styles = _styles()
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=18 * mm,
        title=document_title,
    )
    story: list = []
    page_w = A4[0] - doc.leftMargin - doc.rightMargin

    append_official_clinic_header(story, page_width=page_w, document_title=document_title)
    story.append(Spacer(1, 4))

    # Meta block
    meta_left = [
        f"<b>N° facture :</b> {invoice_number or '—'}",
        f"<b>Patient :</b> {patient_name or '—'}",
        f"<b>N° dossier :</b> {patient_file_number or '—'}",
    ]
    meta_right = [
        f"<b>Date :</b> {printed_date or '—'}",
        f"<b>Heure :</b> {printed_time or '—'}",
        f"<b>Caissier :</b> {printed_by or '—'}",
    ]
    meta_table = Table(
        [
            [
                Paragraph("<br/>".join(meta_left), styles["meta"]),
                Paragraph("<br/>".join(meta_right), styles["meta_right"]),
            ]
        ],
        colWidths=[page_w * 0.55, page_w * 0.45],
    )
    meta_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # Line items
    story.append(Paragraph("Détail des prestations", styles["section"]))
    item_rows = [
        [
            Paragraph("<b>Description</b>", styles["cell"]),
            Paragraph("<b>Qté</b>", styles["cell_right"]),
            Paragraph("<b>Prix unitaire</b>", styles["cell_right"]),
            Paragraph("<b>Total</b>", styles["cell_right"]),
        ]
    ]
    for item in items:
        desc = str(item.get("description", item.get("product_name", "—")))
        qty = int(item.get("quantity") or 1)
        unit = int(item.get("unit_price_gnf") or item.get("amount_gnf") or 0)
        amt = int(item.get("amount_gnf") or item.get("total_gnf") or qty * unit)
        item_rows.append(
            [
                Paragraph(desc, styles["cell"]),
                Paragraph(str(qty), styles["cell_right"]),
                Paragraph(_gnf(unit), styles["cell_right"]),
                Paragraph(_gnf(amt), styles["cell_right"]),
            ]
        )
    if len(item_rows) == 1:
        item_rows.append(
            [
                Paragraph("—", styles["cell"]),
                Paragraph("—", styles["cell_right"]),
                Paragraph("—", styles["cell_right"]),
                Paragraph("—", styles["cell_right"]),
            ]
        )

    items_table = Table(item_rows, colWidths=[page_w * 0.46, page_w * 0.10, page_w * 0.22, page_w * 0.22])
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#134e4a")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 12))

    # Payment summary
    story.append(Paragraph("Récapitulatif paiement", styles["section"]))
    summary_rows = [
        ["Montant total", _gnf(subtotal)],
        ["Exemption", f"{exemption_percent:.0f}% ({_gnf(exemption_amount)})" if exemption_amount else f"{exemption_percent:.0f}%"],
        ["Montant payé", _gnf(paid)],
        ["Reste à payer", _gnf(remaining)],
    ]
    summary_table = Table(summary_rows, colWidths=[page_w * 0.55, page_w * 0.45])
    summary_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), styles["font_bold"]),
                ("FONTNAME", (1, 0), (1, -1), styles["font_reg"]),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#f0fdfa")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#94a3b8")),
                ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#e2e8f0")),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(summary_table)

    if payment_details:
        story.append(Spacer(1, 10))
        story.append(Paragraph("Détail des paiements", styles["section"]))
        pay_rows = []
        for pay in payment_details:
            label = pay.get("label") or METHOD_LABELS.get(pay.get("method", ""), pay.get("method", "—"))
            amount = int(pay.get("amount_gnf") or 0)
            pay_rows.append([label, _gnf(amount)])
        pay_table = Table(pay_rows, colWidths=[page_w * 0.65, page_w * 0.35])
        pay_table.setStyle(
            TableStyle(
                [
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("LINEBELOW", (0, 0), (-1, -2), 0.25, colors.HexColor("#e2e8f0")),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        story.append(pay_table)

    def _footer(canvas, doc_obj):
        canvas.saveState()
        canvas.setFont(styles["font_reg"], 8)
        canvas.setFillColor(colors.grey)
        y = 12 * mm
        canvas.drawString(doc.leftMargin, y + 14, f"Imprimé par : {printed_by or '—'}")
        canvas.drawString(doc.leftMargin, y + 4, f"Date : {printed_date or '—'}    Heure : {printed_time or '—'}")
        canvas.drawCentredString(A4[0] / 2, y + 4, CLINIC_FOOTER_LINE[:90])
        canvas.drawRightString(A4[0] - doc.rightMargin, y + 4, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
