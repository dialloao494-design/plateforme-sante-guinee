"""Simple PDF document generation for invoices and discharge reports."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

CLINIC_PRINT_NAME = "CHFMP – AASMA"
CLINIC_PRINT_NAME_FULL = "CHFMP – AASMA"
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "aasma-clinic-logo.png"
LOGO_DISPLAY_WIDTH = 140  # points (~140 px at 72 dpi)
PAGE_WIDTH = 595
PAGE_HEIGHT = 842


def printed_by_label(user) -> str:
    """Display name for PDF footers (User ORM has no full_name column)."""
    if user is None:
        return "—"
    name = getattr(user, "full_name", None)
    if name:
        return str(name)
    email = getattr(user, "email", None) or ""
    if not email:
        return "—"
    local = email.split("@", 1)[0]
    return local.replace(".", " ").replace("_", " ").strip().title() or email


def _escape_pdf_text(text: str) -> str:
    text = (text or "").replace("\u00a0", " ").replace("\u202f", " ")
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    safe = text.encode("latin-1", errors="replace").decode("latin-1")
    safe = safe.replace("\ufffd", " ")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _read_logo_image() -> tuple[bytes, int, int, str] | None:
    """Return logo bytes, width, height, filter name — JPEG only for simple PDF."""
    if not LOGO_PATH.is_file():
        return None
    data = LOGO_PATH.read_bytes()
    if len(data) >= 3 and data[:3] == b"\xff\xd8\xff":
        width, height = _jpeg_dimensions(data)
        return data, width, height, "DCTDecode"
    return None


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    i = 2
    while i < len(data) - 8:
        if data[i] != 0xFF:
            i += 1
            continue
        marker = data[i + 1]
        if marker in (
            0xC0,
            0xC1,
            0xC2,
            0xC3,
            0xC5,
            0xC6,
            0xC7,
            0xC9,
            0xCA,
            0xCB,
            0xCD,
            0xCE,
            0xCF,
        ):
            height = (data[i + 5] << 8) + data[i + 6]
            width = (data[i + 7] << 8) + data[i + 8]
            return width, height
        if marker in (0xD0, 0xD1, 0xD2, 0xD3, 0xD4, 0xD5, 0xD6, 0xD7, 0xD8, 0xD9, 0x01):
            i += 2
            continue
        seg_len = (data[i + 2] << 8) + data[i + 3]
        i += 2 + seg_len
    raise ValueError("Could not read JPEG dimensions")


def _centered_x(text: str, font_size: float) -> float:
    approx_char = font_size * 0.52
    return max(36.0, (PAGE_WIDTH - len(text) * approx_char) / 2)


def _build_pdf_stream(title: str, lines: list[str], logo_bytes: bytes, logo_w: int, logo_h: int) -> bytes:
    display_w = LOGO_DISPLAY_WIDTH
    display_h = max(1, int(logo_h * display_w / logo_w))
    margin_top = 32
    logo_x = (PAGE_WIDTH - display_w) / 2
    logo_y = PAGE_HEIGHT - margin_top - display_h
    name_y = logo_y - 16
    title_y = name_y - 24
    line_y = title_y - 8

    parts = [
        "q",
        f"{display_w} 0 0 {display_h} {logo_x:.2f} {logo_y:.2f} cm",
        "/Im1 Do",
        "Q",
        "BT",
        "/F1 9 Tf",
        f"1 0 0 1 {_centered_x(CLINIC_PRINT_NAME, 9):.2f} {name_y:.2f} Tm",
        f"({_escape_pdf_text(CLINIC_PRINT_NAME)}) Tj",
        "/F1 12 Tf",
        f"1 0 0 1 50 {title_y:.2f} Tm",
        f"({_escape_pdf_text(title)}) Tj",
    ]

    y = line_y
    for line in lines:
        y -= 16
        if y < 48:
            break
        parts.append("0 -16 Td")
        parts.append(f"({_escape_pdf_text(line)}) Tj")

    parts.append("ET")
    return "\n".join(parts).encode("latin-1", errors="replace")


def _build_pdf_stream_text_only(title: str, lines: list[str]) -> bytes:
    name_y = PAGE_HEIGHT - 48
    title_y = name_y - 24
    line_y = title_y - 8
    parts = [
        "BT",
        "/F1 9 Tf",
        f"1 0 0 1 {_centered_x(CLINIC_PRINT_NAME, 9):.2f} {name_y:.2f} Tm",
        f"({_escape_pdf_text(CLINIC_PRINT_NAME)}) Tj",
        "/F1 12 Tf",
        f"1 0 0 1 50 {title_y:.2f} Tm",
        f"({_escape_pdf_text(title)}) Tj",
    ]
    y = line_y
    for line in lines:
        y -= 16
        if y < 48:
            break
        parts.append("0 -16 Td")
        parts.append(f"({_escape_pdf_text(line)}) Tj")
    parts.append("ET")
    return "\n".join(parts).encode("latin-1", errors="replace")


def build_simple_pdf(title: str, lines: list[str]) -> bytes:
    """A4 PDF with Unicode clinic fonts (French accents) and logo header."""
    from services.simple_pdf_builder import build_unicode_simple_pdf

    return build_unicode_simple_pdf(title, lines)


def build_simple_pdf_legacy(title: str, lines: list[str]) -> bytes:
    """Legacy Helvetica PDF builder retained for offline/debug only."""
    logo = _read_logo_image()
    use_logo = logo is not None
    if use_logo:
        logo_bytes, logo_w, logo_h, _filter = logo
        stream_bytes = _build_pdf_stream(title, lines, logo_bytes, logo_w, logo_h)
    else:
        logo_bytes = b""
        stream_bytes = _build_pdf_stream_text_only(title, lines)

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    if use_logo:
        objects.append(
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> /XObject<< /Im1 6 0 R >> >> >>endobj\n"
        )
    else:
        objects.append(
            b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
            b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
        )
    objects.append(
        f"4 0 obj<< /Length {len(stream_bytes)} >>stream\n".encode()
        + stream_bytes
        + b"\nendstream endobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
    if use_logo:
        img_obj = (
            f"6 0 obj<< /Type /XObject /Subtype /Image /Width {logo_w} /Height {logo_h} "
            f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(logo_bytes)} >>"
            f"stream\n".encode()
            + logo_bytes
            + b"\nendstream endobj\n"
        )
        objects.append(img_obj)

    buf = BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(buf.tell())
        buf.write(obj)
    xref_pos = buf.tell()
    buf.write(f"xref\n0 {len(objects)+1}\n".encode())
    buf.write(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        buf.write(f"{off:010d} 00000 n \n".encode())
    buf.write(b"trailer<< /Size ")
    buf.write(str(len(objects) + 1).encode())
    buf.write(b" /Root 1 0 R >>\nstartxref\n")
    buf.write(str(xref_pos).encode())
    buf.write(b"\n%%EOF")
    return buf.getvalue()


def _gnf(amount: int) -> str:
    return f"{int(amount):,} GNF".replace(",", " ")


def invoice_pdf(
    invoice_number: str,
    patient_name: str,
    items: list[dict],
    *,
    subtotal: int,
    exemption_percent: float = 0,
    exemption_amount: int = 0,
    total: int,
    paid: int,
    payment_methods: list[str] | None = None,
    payment_details: list[dict] | None = None,
    printed_by: str = "",
    printed_at: str = "",
    printed_date: str = "",
    printed_time: str = "",
    patient_file_number: str = "",
    invoice_date: str = "",
    invoice_time: str = "",
    cashier: str = "",
    document_title: str = "FACTURE",
) -> bytes:
    from services.invoice_pdf_builder import build_hospital_invoice_pdf

    footer_date = printed_date or (printed_at.split(" ")[0] if printed_at and " " in printed_at else printed_at)
    footer_time = printed_time or (printed_at.split(" ")[-1] if printed_at and " " in printed_at else "")
    if not payment_details and payment_methods:
        payment_details = [
            {"method": m, "label": m, "amount_gnf": 0} for m in payment_methods
        ]
    return build_hospital_invoice_pdf(
        invoice_number=invoice_number,
        patient_name=patient_name,
        patient_file_number=patient_file_number,
        items=items,
        subtotal=subtotal,
        exemption_percent=exemption_percent,
        exemption_amount=exemption_amount,
        total=total,
        paid=paid,
        payment_details=payment_details,
        printed_by=printed_by,
        printed_date=footer_date,
        printed_time=footer_time,
        invoice_date=invoice_date or footer_date,
        invoice_time=invoice_time or footer_time,
        cashier=cashier or printed_by,
        document_title=document_title,
    )


def invoice_pdf_legacy(invoice_number: str, patient_name: str, items: list[dict], total: int, paid: int) -> bytes:
    """Backward-compatible wrapper."""
    subtotal = sum(int(i.get("amount_gnf") or 0) for i in items) or total
    return invoice_pdf(
        invoice_number,
        patient_name,
        items,
        subtotal=subtotal,
        total=total,
        paid=paid,
    )


def discharge_pdf(patient_name: str, summary: dict) -> bytes:
    lines = [
        f"Patient: {patient_name}",
        f"Type: {summary.get('discharge_type', 'ambulatory')}",
        "",
        f"Diagnostics: {summary.get('diagnoses') or '—'}",
        f"Procédures: {summary.get('procedures') or '—'}",
        f"Médicaments: {summary.get('medications') or '—'}",
        "",
        f"Résumé: {summary.get('clinical_summary') or '—'}",
        f"Suivi: {summary.get('follow_up_instructions') or '—'}",
    ]
    return build_simple_pdf("BON DE SORTIE — Plateforme Santé Guinée", lines)


def imaging_report_pdf(patient_name: str, order: dict, result: dict) -> bytes:
    lines = [
        f"Patient: {patient_name}",
        f"Examen: {order.get('modality', '—')} — {order.get('body_part') or '—'}",
        f"Indication: {order.get('clinical_indication') or '—'}",
        "",
        f"Constats: {result.get('findings') or '—'}",
        f"Conclusion: {result.get('impression') or '—'}",
        f"Recommandations: {result.get('recommendations') or '—'}",
    ]
    return build_simple_pdf("COMPTE-RENDU IMAGERIE MÉDICALE", lines)


def lab_result_pdf(patient_name: str, result: dict) -> bytes:
    from services.lab_report_pdf_builder import build_lab_report_pdf

    return build_lab_report_pdf(
        patient_name=patient_name,
        patient_file_number=str(result.get("patient_file_number") or ""),
        test_name=str(result.get("test_name") or ""),
        template_id=result.get("template_id"),
        result_data=result.get("result_data"),
        result_summary=result.get("result_summary"),
        technician=str(result.get("technician") or ""),
        validated_date=str(result.get("validated_date") or ""),
        validated_time=str(result.get("validated_time") or ""),
    )


def clinical_report_pdf(summary: dict) -> bytes:
    rev = summary.get("revenue") or {}
    lines = [
        f"Période: {summary.get('period_start')} → {summary.get('period_end')}",
        "",
        f"RDV total: {summary.get('appointments_total', 0)}",
        f"RDV complétés: {summary.get('appointments_completed', 0)}",
        f"Consultations: {summary.get('consultations', 0)}",
        f"Labo: {summary.get('lab_orders', 0)} · Imagerie: {summary.get('imaging_orders', 0)}",
        f"Pharmacie délivrée: {summary.get('pharmacy_dispensed', 0)}",
        f"Admissions: {summary.get('admissions', 0)} · Sorties: {summary.get('discharges', 0)}",
        "",
        f"Recettes totales: {rev.get('total_collected_gnf', 0):,} GNF".replace(",", " "),
        f"Factures payées: {rev.get('paid_invoices_count', 0)}",
        f"Charges en attente: {rev.get('pending_charges_count', 0)}",
    ]
    return build_simple_pdf("RAPPORT CLINIQUE — Plateforme Santé Guinée", lines)


def refund_receipt_pdf(refund, clinic_name: str = "", printed_by: str = "") -> bytes:
    from datetime import datetime

    from services.refund_receipt_pdf_builder import build_refund_receipt_pdf

    patient_name = "—"
    patient_number = ""
    if getattr(refund, "patient", None):
        patient_name = f"{refund.patient.first_name} {refund.patient.last_name}".strip()
        patient_number = getattr(refund.patient, "patient_number", None) or getattr(refund.patient, "mrn", None) or ""
    invoice_number = refund.invoice.invoice_number if getattr(refund, "invoice", None) else "—"
    now = datetime.now()
    reason_notes = getattr(refund, "reason_notes", None) or getattr(refund, "notes", None) or ""
    return build_refund_receipt_pdf(
        clinic_name=clinic_name or "",
        refund_number=getattr(refund, "refund_number", "") or "",
        invoice_number=invoice_number or "",
        patient_name=patient_name,
        patient_number=patient_number or "",
        service_paid_for=getattr(refund, "service_paid_for", None) or "",
        amount_consumed_gnf=int(getattr(refund, "amount_consumed_gnf", 0) or 0),
        refund_amount_gnf=int(getattr(refund, "refund_amount_gnf", 0) or 0),
        reason=getattr(refund, "reason", None) or "",
        reason_notes=reason_notes or "",
        recipient_name=getattr(refund, "recipient_name", None) or "",
        recipient_phone=getattr(refund, "recipient_phone", None) or "",
        refund_method=getattr(refund, "refund_method", None) or "",
        status=getattr(refund, "status", None) or "",
        printed_by=printed_by or "",
        printed_date=now.strftime("%d/%m/%Y"),
        printed_time=now.strftime("%H:%M"),
    )
