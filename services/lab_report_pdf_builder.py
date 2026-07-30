"""Official AASMA laboratory report PDF — matches clinic paper templates."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from data.lab_report_templates import (
    CLINIC_LAB_FOOTER_ADDRESS,
    CLINIC_LAB_FOOTER_CONTACT,
    TEMPLATES,
    detect_template_id,
)
from data.clinic_branding import CLINIC_FOOTER_LINE
from services.clinic_print_header import append_official_clinic_header
from core.output_encoding import escape_pdf_paragraph

LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "aasma-clinic-logo.png"
TITLE_COLOR = colors.HexColor("#C9A227")


def _parse_payload(result_data: str | None) -> dict:
    if not result_data:
        return {}
    try:
        return json.loads(result_data) or {}
    except (json.JSONDecodeError, TypeError):
        return {}


def _p(text: object, style=None) -> Paragraph:
    style = style or getSampleStyleSheet()["Normal"]
    return Paragraph(escape_pdf_paragraph(text).replace("\n", "<br/>"), style)

def _footer(canvas, doc):
    canvas.saveState()
    w, _ = A4
    y = 14 * mm
    canvas.setStrokeColor(TITLE_COLOR)
    canvas.setLineWidth(0.8)
    canvas.line(doc.leftMargin, y + 10 * mm, w - doc.rightMargin, y + 10 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(colors.HexColor("#334155"))
    canvas.drawCentredString(w / 2, y + 6 * mm, CLINIC_LAB_FOOTER_ADDRESS)
    canvas.drawCentredString(w / 2, y + 1.5 * mm, CLINIC_LAB_FOOTER_CONTACT)
    canvas.restoreState()


def _title_style():
    base = getSampleStyleSheet()
    return ParagraphStyle(
        "LabTitle",
        parent=base["Heading1"],
        fontName="Helvetica-Bold",
        fontSize=13,
        textColor=TITLE_COLOR,
        alignment=TA_CENTER,
        spaceAfter=10,
    )


def _parse_rows(result_data: str | None, result_summary: str | None) -> dict[str, str]:
    out: dict[str, str] = {}
    payload = _parse_payload(result_data)
    for row in payload.get("rows") or []:
        p = str(row.get("parameter") or "").strip()
        if p:
            out[p] = str(row.get("result") or "").strip()
    if not out and result_summary:
        for part in result_summary.split("·"):
            if ":" in part:
                k, v = part.split(":", 1)
                out[k.strip()] = v.strip()
    return out


def build_lab_report_pdf(
    *,
    patient_name: str,
    patient_file_number: str,
    test_name: str,
    template_id: str | None = None,
    result_data: str | None = None,
    result_summary: str | None = None,
    technician: str = "",
    validated_date: str = "",
    validated_time: str = "",
) -> bytes:
    tid = template_id or detect_template_id(test_name)
    tpl = TEMPLATES.get(tid or "")
    payload = _parse_payload(result_data)
    values = _parse_rows(result_data, result_summary)

    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=12 * mm,
        bottomMargin=22 * mm,
    )
    story = []
    page_w = A4[0] - doc.leftMargin - doc.rightMargin

    append_official_clinic_header(story, page_width=page_w, document_title=tpl["title"] if tpl else (test_name or "Résultat laboratoire"))
    story.append(Spacer(1, 4))

    meta = (
        f"<b>Patient :</b> {escape_pdf_paragraph(patient_name or '—')} &nbsp;&nbsp; "
        f"<b>N° dossier :</b> {escape_pdf_paragraph(patient_file_number or '—')}"
    )
    if technician:
        meta += f" &nbsp;&nbsp; <b>Technicien :</b> {escape_pdf_paragraph(technician)}"
    if validated_date:
        meta += f" &nbsp;&nbsp; <b>Date :</b> {escape_pdf_paragraph(validated_date)}"
    if validated_time:
        meta += f" &nbsp;&nbsp; <b>Heure :</b> {escape_pdf_paragraph(validated_time)}"
    story.append(Paragraph(meta, getSampleStyleSheet()["Normal"]))
    story.append(Spacer(1, 8))

    macro_text = (payload.get("macro_appearance") or "").strip()
    if tpl and tpl.get("type") == "ecbu" and macro_text:
        story.append(
            Paragraph(
                f"<b>Aspect macroscopique :</b> {escape_pdf_paragraph(macro_text)}",
                getSampleStyleSheet()["Normal"],
            )
        )
        story.append(Spacer(1, 6))

    if tpl and tpl.get("type") == "hemogram":
        header = ["Paramètres", "Résultats", "Unités", "Enfant", "Homme", "Femme"]
        data = [header]
        for row in tpl["rows"]:
            p = row["parameter"]
            data.append([
                escape_pdf_paragraph(p),
                escape_pdf_paragraph(values.get(p, "")),
                escape_pdf_paragraph(row.get("unit", "")),
                escape_pdf_paragraph(row.get("ref_child", "")),
                escape_pdf_paragraph(row.get("ref_male", "")),
                escape_pdf_paragraph(row.get("ref_female", "")),
            ])
        col_w = [page_w * 0.16, page_w * 0.14, page_w * 0.12, page_w * 0.19, page_w * 0.19, page_w * 0.19]
    elif tpl and tpl.get("type") == "ecbu":
        header = ["Paramètres", "Résultats", "Unité", "Référence"]
        data = [header]
        for row in tpl["rows"]:
            p = row["parameter"]
            data.append([
                escape_pdf_paragraph(p),
                escape_pdf_paragraph(values.get(p, "")),
                escape_pdf_paragraph(row.get("unit", "")),
                escape_pdf_paragraph(row.get("reference", "")),
            ])
        col_w = [page_w * 0.28, page_w * 0.22, page_w * 0.15, page_w * 0.35]
    elif tpl and tpl.get("type") == "bu":
        header = ["Paramètre", "Résultat", "Référence"]
        data = [header]
        for row in tpl["rows"]:
            p = row["parameter"]
            data.append([
                escape_pdf_paragraph(p),
                escape_pdf_paragraph(values.get(p, "")),
                escape_pdf_paragraph(row.get("reference", "")),
            ])
        col_w = [page_w * 0.35, page_w * 0.30, page_w * 0.35]
    else:
        header = ["Paramètre", "Résultat", "Référence"]
        data = [header]
        if values:
            for p, v in values.items():
                data.append([escape_pdf_paragraph(p), escape_pdf_paragraph(v), ""])
        elif result_summary:
            data.append([
                escape_pdf_paragraph(test_name or "—"),
                escape_pdf_paragraph(result_summary),
                "",
            ])
        col_w = [page_w * 0.35, page_w * 0.35, page_w * 0.30]

    table = Table(data, colWidths=col_w, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#FFF8E7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#92400e")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(table)

    if tpl and tpl.get("note"):
        story.append(Spacer(1, 10))
        story.append(
            Paragraph(
                f"<b>{escape_pdf_paragraph(tpl['note'])}</b>",
                getSampleStyleSheet()["Normal"],
            )
        )

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()
