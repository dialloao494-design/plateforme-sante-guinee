"""Official AASMA refund receipt PDF (ReportLab) — same header as invoices."""

from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from data.clinic_branding import CLINIC_FOOTER_LINE
from services.clinic_print_header import append_official_clinic_header
from services.pdf_fonts import ensure_clinic_fonts

REASON_LABELS = {
    "deceased": "Décès",
    "service_cancelled": "Service annulé",
    "overpayment": "Trop-perçu",
    "other": "Autre",
}

METHOD_LABELS = {
    "cash": "Espèces",
    "orange_money": "Orange Money",
    "bank_transfer": "Virement bancaire",
    "card": "Carte bancaire",
    "insurance_adjustment": "Assurance",
    "insurance": "Assurance",
}

STATUS_LABELS = {
    "pending": "En attente",
    "approved": "Approuvé",
    "rejected": "Rejeté",
    "paid": "Payé",
}


def _gnf(amount: int) -> str:
    return f"{int(amount or 0):,} GNF".replace(",", " ")


def _esc(value) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def build_refund_receipt_pdf(
    *,
    clinic_name: str = "",
    refund_number: str = "",
    invoice_number: str = "",
    patient_name: str = "",
    patient_number: str = "",
    service_paid_for: str = "",
    amount_consumed_gnf: int = 0,
    refund_amount_gnf: int = 0,
    reason: str = "",
    reason_notes: str = "",
    recipient_name: str = "",
    recipient_phone: str = "",
    refund_method: str = "",
    status: str = "",
    printed_by: str = "",
    printed_date: str = "",
    printed_time: str = "",
) -> bytes:
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=12 * mm,
        bottomMargin=18 * mm,
        title="Reçu de remboursement",
    )
    page_w = A4[0] - doc.leftMargin - doc.rightMargin
    font_reg, font_bold = ensure_clinic_fonts()
    base = getSampleStyleSheet()
    meta = ParagraphStyle("RefundMeta", parent=base["Normal"], fontName=font_reg, fontSize=10, leading=14)
    meta_right = ParagraphStyle(
        "RefundMetaR", parent=base["Normal"], fontName=font_reg, fontSize=10, leading=14, alignment=TA_RIGHT
    )
    section = ParagraphStyle(
        "RefundSection",
        parent=base["Normal"],
        fontName=font_bold,
        fontSize=11,
        textColor=colors.HexColor("#0f766e"),
        spaceBefore=8,
        spaceAfter=4,
    )
    cell = ParagraphStyle("RefundCell", parent=base["Normal"], fontName=font_reg, fontSize=10, leading=13)
    cell_b = ParagraphStyle("RefundCellB", parent=cell, fontName=font_bold)
    footer = ParagraphStyle(
        "RefundFooter", parent=base["Normal"], fontName=font_reg, fontSize=8, textColor=colors.HexColor("#475569")
    )

    story: list = []
    append_official_clinic_header(story, page_width=page_w, document_title="REÇU DE REMBOURSEMENT")
    story.append(Spacer(1, 4))

    if clinic_name:
        story.append(Paragraph(f"<b>Clinique :</b> {_esc(clinic_name)}", meta))
        story.append(Spacer(1, 4))

    left = [
        f"<b>N° remboursement :</b> {_esc(refund_number or '—')}",
        f"<b>Facture :</b> {_esc(invoice_number or '—')}",
        f"<b>Patient :</b> {_esc(patient_name or '—')}",
        f"<b>N° dossier :</b> {_esc(patient_number or '—')}",
    ]
    right = [
        f"<b>Date :</b> {_esc(printed_date or '—')}",
        f"<b>Heure :</b> {_esc(printed_time or '—')}",
        f"<b>Imprimé par :</b> {_esc(printed_by or '—')}",
    ]
    meta_table = Table(
        [[Paragraph("<br/>".join(left), meta), Paragraph("<br/>".join(right), meta_right)]],
        colWidths=[page_w * 0.58, page_w * 0.42],
    )
    meta_table.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"), ("BOTTOMPADDING", (0, 0), (-1, -1), 6)]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    story.append(Paragraph("Détail du remboursement", section))
    reason_label = REASON_LABELS.get(reason, reason or "—")
    if reason == "other" and reason_notes:
        reason_label = f"Autre — {reason_notes}"
    elif reason_notes and reason != "other":
        reason_label = f"{reason_label} ({reason_notes})"

    rows = [
        [Paragraph("<b>Libellé</b>", cell_b), Paragraph("<b>Valeur</b>", cell_b)],
        [Paragraph("Service payé", cell), Paragraph(_esc(service_paid_for or "—"), cell)],
        [Paragraph("Montant consommé", cell), Paragraph(_gnf(amount_consumed_gnf), cell)],
        [Paragraph("Montant remboursé", cell), Paragraph(_gnf(refund_amount_gnf), cell)],
        [Paragraph("Motif", cell), Paragraph(_esc(reason_label), cell)],
        [Paragraph("Bénéficiaire", cell), Paragraph(_esc(recipient_name or "—"), cell)],
        [Paragraph("Téléphone", cell), Paragraph(_esc(recipient_phone or "—"), cell)],
        [Paragraph("Mode de remboursement", cell), Paragraph(_esc(METHOD_LABELS.get(refund_method, refund_method or "—")), cell)],
        [Paragraph("Statut", cell), Paragraph(_esc(STATUS_LABELS.get(status, status or "—")), cell)],
    ]
    detail = Table(rows, colWidths=[page_w * 0.42, page_w * 0.58])
    detail.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#ecfdf5")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#134e4a")),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 7),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(detail)
    story.append(Spacer(1, 18))
    story.append(Paragraph(CLINIC_FOOTER_LINE, footer))

    def _footer(canvas, _doc):
        canvas.saveState()
        w, _ = A4
        canvas.setFont(font_reg, 8)
        canvas.setFillColor(colors.HexColor("#64748b"))
        canvas.drawCentredString(w / 2, 10 * mm, CLINIC_FOOTER_LINE)
        canvas.restoreState()

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
