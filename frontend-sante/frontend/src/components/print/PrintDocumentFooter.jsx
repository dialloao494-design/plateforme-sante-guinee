import './print-documents.css';

/** Standard footer for all reception printable documents. */
export default function PrintDocumentFooter({
  printedBy = '',
  department = 'Réception',
  pageLabel = 'Page 1 sur 1',
}) {
  const now = new Date();
  const dateStr = now.toLocaleDateString('fr-FR');
  const timeStr = now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });

  return (
    <footer className="print-document-footer">
      <div className="print-document-footer__grid">
        <div>
          <strong>Imprimé le :</strong>
          <span>{dateStr} — {timeStr}</span>
        </div>
        <div>
          <strong>Département :</strong>
          <span>{department}</span>
        </div>
        <div>
          <strong>Imprimé par :</strong>
          <span>{printedBy || '—'}</span>
        </div>
        <div>
          <strong>{pageLabel}</strong>
        </div>
      </div>
    </footer>
  );
}
