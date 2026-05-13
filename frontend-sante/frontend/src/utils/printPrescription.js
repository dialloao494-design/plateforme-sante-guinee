function escapeHtml(s) {
  return String(s ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

/**
 * Opens a print dialog with a simple ordonnance layout (no PDF dependency).
 * @param {{ doctorName?: string, patientName?: string, bodyText: string, issuedAt?: Date }} opts
 * @returns {boolean} false if popup blocked
 */
export function printPrescriptionHtml({ doctorName, patientName, bodyText, issuedAt = new Date() }) {
  const w = window.open('', '_blank', 'noopener,noreferrer,width=720,height=900');
  if (!w) return false;

  const bodyHtml = escapeHtml(bodyText).replace(/\n/g, '<br/>');
  const docTitle = 'Ordonnance';
  const dateStr = issuedAt.toLocaleString('fr-GN', { dateStyle: 'long', timeStyle: 'short' });

  w.document.write(`<!DOCTYPE html>
<html lang="fr">
<head>
  <meta charset="utf-8" />
  <title>${escapeHtml(docTitle)}</title>
  <style>
    @page { margin: 18mm; }
    body { font-family: Georgia, 'Times New Roman', serif; color: #111; line-height: 1.45; max-width: 640px; margin: 24px auto; padding: 0 12px; }
    h1 { font-size: 1.25rem; letter-spacing: 0.04em; text-transform: uppercase; border-bottom: 2px solid #0d5c4d; padding-bottom: 8px; }
    .meta { font-size: 0.9rem; margin: 16px 0; }
    .meta dt { font-weight: 600; display: inline; }
    .meta dd { display: inline; margin: 0 1.5rem 0 0.35rem; }
    .rx { margin-top: 28px; min-height: 200px; font-size: 1.05rem; }
    .foot { margin-top: 48px; font-size: 0.85rem; color: #444; }
    @media print {
      body { margin: 0; max-width: none; }
      .no-print { display: none !important; }
    }
  </style>
</head>
<body>
  <h1>Ordonnance médicale</h1>
  <dl class="meta">
    <dt>Date</dt><dd>${escapeHtml(dateStr)}</dd>
    ${patientName ? `<dt>Patient</dt><dd>${escapeHtml(patientName)}</dd>` : ''}
    ${doctorName ? `<dt>Prescripteur</dt><dd>${escapeHtml(doctorName)}</dd>` : ''}
  </dl>
  <div class="rx">${bodyHtml}</div>
  <p class="foot">Document généré depuis la plateforme — conserver pour votre dossier.</p>
  <p class="no-print" style="margin-top:24px;font-family:system-ui,sans-serif;font-size:0.85rem;">Si l’impression ne démarre pas, utilisez le menu du navigateur (Ctrl+P).</p>
</body>
</html>`);
  w.document.close();
  w.focus();
  w.print();
  return true;
}
