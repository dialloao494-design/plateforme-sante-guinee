"""Simple PDF document generation for invoices and discharge reports."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

CLINIC_PRINT_NAME = "CHFM – POLYCLINIQUE AASMA"
CLINIC_PRINT_NAME_FULL = "POLYCLINIQUE MÉDICO-CHIRURGICALE AASMA"
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "branding" / "aasma-clinic-logo.png"
LOGO_DISPLAY_WIDTH = 140  # points (~140 px at 72 dpi)
PAGE_WIDTH = 595
PAGE_HEIGHT = 842


def _escape_pdf_text(text: str) -> str:
    safe = text.encode("latin-1", errors="replace").decode("latin-1")
    return safe.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


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


def build_simple_pdf(title: str, lines: list[str]) -> bytes:
    """Minimal PDF generator with centered clinic logo header."""
    logo_bytes = LOGO_PATH.read_bytes()
    logo_w, logo_h = _jpeg_dimensions(logo_bytes)
    stream_bytes = _build_pdf_stream(title, lines, logo_bytes, logo_w, logo_h)

    img_obj = (
        f"6 0 obj<< /Type /XObject /Subtype /Image /Width {logo_w} /Height {logo_h} "
        f"/ColorSpace /DeviceRGB /BitsPerComponent 8 /Filter /DCTDecode /Length {len(logo_bytes)} >>"
        f"stream\n".encode()
        + logo_bytes
        + b"\nendstream endobj\n"
    )

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
    objects.append(
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources<< /Font<< /F1 5 0 R >> /XObject<< /Im1 6 0 R >> >> >>endobj\n"
    )
    objects.append(
        f"4 0 obj<< /Length {len(stream_bytes)} >>stream\n".encode()
        + stream_bytes
        + b"\nendstream endobj\n"
    )
    objects.append(b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n")
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


PAYMENT_METHOD_LABELS = {
    "cash": "Espèces",
    "orange_money": "Orange Money",
    "bank_transfer": "Virement bancaire",
    "card": "Carte bancaire",
    "insurance": "Assurance",
    "mtn": "MTN MoMo",
}


def _payment_method_label(method: str) -> str:
    return PAYMENT_METHOD_LABELS.get(method, method.replace("_", " ").title())


def _payment_breakdown_line(label: str, amount: int, width: int = 40) -> str:
    dots = max(2, width - len(label) - len(_gnf(amount)))
    return f"{label}{'.' * dots}{_gnf(amount)}"


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
    payment_lines: list[dict] | None = None,
    printed_by: str = "",
    printed_at: str = "",
) -> bytes:
    remaining = max(0, total - paid)
    lines = [
        f"Patient: {patient_name}",
        f"Facture: {invoice_number}",
        "",
        "Produit / Service          Qté   Prix U        Total",
        "--------------------------------------------------------",
    ]
    for item in items:
        desc = str(item.get("description", "—"))[:26]
        qty = int(item.get("quantity") or 1)
        unit = int(item.get("unit_price_gnf") or item.get("amount_gnf") or 0)
        amt = int(item.get("amount_gnf") or qty * unit)
        lines.append(f"{desc:<26} {qty:>3} {_gnf(unit):>12} {_gnf(amt):>12}")
    lines.extend(
        [
            "",
            "Récapitulatif paiement",
            f"Montant total: {_gnf(subtotal)}",
            f"Exemption (%): {exemption_percent:.0f}%",
            f"Montant exemption: {_gnf(exemption_amount)}",
            f"Nouveau total: {_gnf(total)}",
        ]
    )
    if payment_lines:
        lines.append("")
        lines.append("Détail des paiements")
        for entry in payment_lines:
            label = _payment_method_label(str(entry.get("payment_method") or "—"))
            amount = int(entry.get("amount_gnf") or 0)
            lines.append(_payment_breakdown_line(label, amount))
            reference = entry.get("reference")
            if reference:
                lines.append(f"  Réf.: {reference}")
        lines.append("")
        lines.append(_payment_breakdown_line("Total payé", paid))
        lines.append(_payment_breakdown_line("Reste à payer", remaining))
    else:
        lines.extend(
            [
                f"Montant reçu: {_gnf(paid)}",
                f"Reste à payer: {_gnf(remaining)}",
                f"Mode(s) de paiement: {', '.join(payment_methods or []) or '—'}",
            ]
        )
    lines.extend(
        [
            "",
            f"Imprimé par: {printed_by or '—'}",
            printed_at or "",
            "Page 1 sur 1",
        ]
    )
    return build_simple_pdf("FACTURE", lines)


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
    lines = [
        f"Patient: {patient_name}",
        f"Examen: {result.get('test_name', '—')} ({result.get('test_code', '—')})",
        "",
        f"Résultat: {result.get('result_summary') or '—'}",
        f"Référence: {result.get('reference_range') or '—'}",
        f"Interprétation: {result.get('interpretation') or '—'}",
        f"Validé le: {result.get('validated_at') or '—'}",
    ]
    return build_simple_pdf("RÉSULTAT LABORATOIRE", lines)


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


def refund_receipt_pdf(refund, clinic_name: str = "") -> bytes:
    patient_name = "—"
    if getattr(refund, "patient", None):
        patient_name = f"{refund.patient.first_name} {refund.patient.last_name}".strip()
    invoice_number = refund.invoice.invoice_number if getattr(refund, "invoice", None) else "—"
    lines = [
        f"Clinique: {clinic_name or '—'}",
        f"Patient: {patient_name}",
        f"N° remboursement: {refund.refund_number}",
        f"Facture: {invoice_number}",
        f"Service: {refund.service_paid_for or '—'}",
        f"Montant consommé: {refund.amount_consumed_gnf:,} GNF".replace(",", " "),
        f"Montant remboursé: {refund.refund_amount_gnf:,} GNF".replace(",", " "),
        f"Motif: {refund.reason}",
        f"Bénéficiaire: {refund.recipient_name or '—'} ({refund.recipient_relationship or '—'})",
        f"Tél: {refund.recipient_phone or '—'}",
        f"Mode: {refund.refund_method or '—'}",
        f"Statut: {refund.status}",
    ]
    return build_simple_pdf("REÇU DE REMBOURSEMENT", lines)
