"""Official AASMA medical consultation report PDF."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    KeepTogether,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from data.clinic_branding import CLINIC_FOOTER_LINE
from services.clinic_print_header import append_official_clinic_header

TITLE_COLOR = colors.HexColor("#C9A227")
TEAL = colors.HexColor("#134e4a")


def _footer_factory(printed_by: str, department: str):
    def _footer(canvas, doc):
        canvas.saveState()
        w, _ = A4
        y = 12 * mm
        canvas.setStrokeColor(TITLE_COLOR)
        canvas.setLineWidth(0.8)
        canvas.line(doc.leftMargin, y + 8 * mm, w - doc.rightMargin, y + 8 * mm)
        canvas.setFont("Helvetica", 7.5)
        canvas.setFillColor(colors.HexColor("#334155"))
        left = f"Imprimé par : {printed_by} · {department}"
        canvas.drawString(doc.leftMargin, y + 3.5 * mm, left)
        canvas.drawRightString(
            w - doc.rightMargin, y + 3.5 * mm, f"Page {doc.page}"
        )
        canvas.drawCentredString(w / 2, y - 0.5 * mm, CLINIC_FOOTER_LINE)
        canvas.restoreState()

    return _footer


def _section(story, heading_style, body_style, title: str, value):
    text = (value or "").strip() if isinstance(value, str) else value
    if not text:
        return
    story.append(Paragraph(title, heading_style))
    story.append(Paragraph(str(text).replace("\n", "<br/>"), body_style))
    story.append(Spacer(1, 4))


def build_consultation_pdf(data: dict) -> bytes:
    """`data` keys: patient (dict), consultation (dict), vitals (dict),
    lab_orders (list), imaging_orders (list), prescriptions (list),
    doctor_name, printed_by, department, specialty_label."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=24 * mm,
        title="Compte rendu de consultation",
    )
    page_width = doc.width
    base = getSampleStyleSheet()
    heading = ParagraphStyle(
        "SecHeading",
        parent=base["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        textColor=TEAL,
        spaceBefore=6,
        spaceAfter=2,
    )
    body = ParagraphStyle(
        "SecBody", parent=base["Normal"], fontSize=9.5, leading=12.5
    )
    label = ParagraphStyle(
        "Label", parent=base["Normal"], fontSize=8.5, textColor=colors.HexColor("#64748b")
    )
    val = ParagraphStyle("Val", parent=base["Normal"], fontSize=9.5, fontName="Helvetica-Bold")

    story: list = []
    append_official_clinic_header(
        story, page_width=page_width, document_title="COMPTE RENDU DE CONSULTATION MÉDICALE"
    )

    patient = data.get("patient") or {}
    consult = data.get("consultation") or {}
    vitals = data.get("vitals") or {}

    # Patient identity block
    ident_rows = [
        [Paragraph("N° dossier", label), Paragraph(str(patient.get("patient_number") or "—"), val),
         Paragraph("Date", label), Paragraph(str(data.get("date") or datetime.now().strftime("%d/%m/%Y %H:%M")), val)],
        [Paragraph("Nom complet", label), Paragraph(str(patient.get("full_name") or "—"), val),
         Paragraph("Âge / Sexe", label), Paragraph(f"{patient.get('age') or '—'} / {patient.get('sex') or '—'}", val)],
        [Paragraph("Téléphone", label), Paragraph(str(patient.get("phone") or "—"), val),
         Paragraph("Prise en charge", label), Paragraph(str(patient.get("payer") or "—"), val)],
    ]
    ident = Table(ident_rows, colWidths=[page_width * 0.16, page_width * 0.34, page_width * 0.18, page_width * 0.32])
    ident.setStyle(
        TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
                ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(ident)
    story.append(Spacer(1, 8))

    # Vitals
    if vitals:
        vrows = [[
            Paragraph("T°", label), Paragraph(f"{vitals.get('temperature_c') or '—'} °C", val),
            Paragraph("TA", label), Paragraph(f"{vitals.get('bp_systolic') or '—'}/{vitals.get('bp_diastolic') or '—'}", val),
            Paragraph("FC", label), Paragraph(f"{vitals.get('heart_rate') or '—'}", val),
            Paragraph("FR", label), Paragraph(f"{vitals.get('respiratory_rate') or '—'}", val),
        ], [
            Paragraph("Poids", label), Paragraph(f"{vitals.get('weight_kg') or '—'} kg", val),
            Paragraph("Taille", label), Paragraph(f"{vitals.get('height_cm') or '—'} cm", val),
            Paragraph("IMC", label), Paragraph(f"{vitals.get('bmi') or '—'}", val),
            Paragraph("", label), Paragraph("", val),
        ]]
        vt = Table(vrows, colWidths=[page_width * 0.07, page_width * 0.18] * 4)
        vt.setStyle(
            TableStyle(
                [
                    ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#cbd5e1")),
                    ("INNERGRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#e2e8f0")),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(Paragraph("Signes vitaux (dernière évaluation)", heading))
        story.append(Spacer(1, 2))
        story.append(vt)
        story.append(Spacer(1, 6))

    _section(story, heading, body, "Motif de consultation", consult.get("chief_complaint"))
    _section(story, heading, body, "Histoire de la maladie", consult.get("history"))
    _section(story, heading, body, "Antécédents médicaux", consult.get("medical_history"))
    _section(story, heading, body, "Antécédents chirurgicaux", consult.get("surgical_history"))
    _section(story, heading, body, "Antécédents gynéco-obstétricaux", consult.get("gyneco_history"))
    _section(story, heading, body, "Allergies", consult.get("allergies"))
    _section(story, heading, body, "Traitements en cours", consult.get("current_treatments"))
    _section(story, heading, body, "Examen clinique", consult.get("examination"))
    _section(story, heading, body, "Diagnostic", consult.get("diagnosis"))
    _section(story, heading, body, "Plan de traitement", consult.get("treatment_plan"))
    _section(story, heading, body, "Observations / Notes", consult.get("observations"))
    _section(story, heading, body, "Service / Spécialité", data.get("specialty_label"))

    # Requested services
    labs = data.get("lab_orders") or []
    imaging = data.get("imaging_orders") or []
    rx = data.get("prescriptions") or []
    if labs or imaging or rx:
        story.append(Paragraph("Examens & prescriptions demandés", heading))
        lines = []
        for o in labs:
            lines.append(f"• Laboratoire : {o}")
        for o in imaging:
            lines.append(f"• Imagerie : {o}")
        for o in rx:
            lines.append(f"• Ordonnance : {o}")
        story.append(Paragraph("<br/>".join(lines), body))
        story.append(Spacer(1, 6))

    story.append(Spacer(1, 14))
    sign = Table(
        [[Paragraph(f"Médecin : <b>{data.get('doctor_name') or '—'}</b>", body),
          Paragraph("Signature / Cachet", label)]],
        colWidths=[page_width * 0.55, page_width * 0.45],
    )
    sign.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP")]))
    story.append(KeepTogether(sign))

    footer = _footer_factory(data.get("printed_by") or "—", data.get("department") or "Médecine")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buf.getvalue()
