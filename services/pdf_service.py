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
