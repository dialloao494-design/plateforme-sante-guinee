"""Simple PDF document generation for invoices and discharge reports."""

from __future__ import annotations

from io import BytesIO


def _escape_pdf_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_simple_pdf(title: str, lines: list[str]) -> bytes:
    """Minimal PDF generator — no external dependencies."""
    content_lines = ["BT", "/F1 12 Tf", "50 780 Td", f"({ _escape_pdf_text(title) }) Tj"]
    y = 760
    for line in lines:
        y -= 16
        if y < 50:
            break
        content_lines.append(f"0 -16 Td ({_escape_pdf_text(line)}) Tj")
    content_lines.append("ET")
    stream = "\n".join(content_lines)
    stream_bytes = stream.encode("latin-1", errors="replace")

    objects: list[bytes] = []
    objects.append(b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n")
    objects.append(b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n")
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

    buf = BytesIO()
    buf.write(b"%PDF-1.4\n")
    offsets = [0]
    for i, obj in enumerate(objects, start=1):
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


def invoice_pdf(invoice_number: str, patient_name: str, items: list[dict], total: int, paid: int) -> bytes:
    lines = [
        f"Patient: {patient_name}",
        f"Facture: {invoice_number}",
        "",
        "Détail:",
    ]
    for item in items:
        lines.append(f"- {item['description']}: {item['amount_gnf']:,} GNF".replace(",", " "))
    lines.extend(["", f"Total: {total:,} GNF".replace(",", " "), f"Payé: {paid:,} GNF".replace(",", " ")])
    return build_simple_pdf("FACTURE — Plateforme Santé Guinée", lines)


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
    return build_simple_pdf("COMPTE-RENDU IMAGERIE — Plateforme Santé Guinée", lines)


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
    return build_simple_pdf("RÉSULTAT LABORATOIRE — Plateforme Santé Guinée", lines)


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
