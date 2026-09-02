import { useCallback, useEffect, useMemo, useState } from 'react';
import clinicalApi from '../../../services/clinicalApi.js';
import { formatApiError } from '../../../utils/apiError.js';
import { formatClinicalDate, formatClinicalTime } from '../../../utils/clinicalPresentation.js';
import { downloadAuthenticatedPdf } from '../../../utils/downloadPdf.js';

const STATUS = { dispensed: 'Délivrée', partially_dispensed: 'Partielle', cancelled: 'Annulée' };

export default function PharmacyHistoryTab() {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
  const [printingId, setPrintingId] = useState(null);
  const load = useCallback(async () => {
    try { const { data } = await clinicalApi.pharmacyQueue({ scope: 'history' }); setRows(data || []); }
    catch (err) { setError(formatApiError(err, 'Chargement de l’historique impossible')); }
  }, []);
  useEffect(() => { void load(); }, [load]);
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) => [row.request_number, row.patient_name, row.medications, row.prepared_by].some((value) => String(value || '').toLowerCase().includes(q)));
  }, [query, rows]);
  const reprint = async (row) => {
    if (!row.charge_id) return;
    setPrintingId(row.id);
    setError('');
    try {
      await downloadAuthenticatedPdf(`/clinical/pharmacy/charges/${row.charge_id}/receipt`, `facture-${row.invoice_number || row.charge_id}.pdf`);
    } catch (err) {
      setError(formatApiError(err, 'Réimpression impossible'));
    } finally {
      setPrintingId(null);
    }
  };
  return <section className="pharmacy-panel" aria-labelledby="pharmacy-history-title">
    <div className="pharmacy-panel-header"><div><p className="pharmacy-section-kicker">Traçabilité</p><h2 id="pharmacy-history-title">Historique des dispensations</h2></div><label className="pharmacy-history-search">Rechercher<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="N°, patient ou médicament…" /></label></div>
    {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}
    <div className="pharmacy-table-wrap" tabIndex="0" role="region" aria-label="Historique des patients servis">
      <table className="pharmacy-table"><thead><tr><th>N° demande</th><th>Date et heure</th><th>Patient</th><th>Médicaments</th><th>Délivré par</th><th>État</th><th>Facture</th></tr></thead>
        <tbody>{filtered.length ? filtered.map((row) => <tr key={row.id}><td><strong>{row.request_number}</strong></td><td>{formatClinicalDate(row.dispensed_at || row.created_at)}<br/><small>{formatClinicalTime(row.dispensed_at || row.created_at)}</small></td><td>{row.patient_name || '—'}</td><td>{row.medications || '—'}</td><td>{row.prepared_by || '—'}</td><td><span className={`pharmacy-badge pharmacy-badge--${row.status === 'dispensed' ? 'success' : row.status === 'cancelled' ? 'muted' : 'info'}`}>{STATUS[row.status] || row.status}</span></td><td>{row.status === 'dispensed' && row.charge_id ? <button type="button" className="clinical-btn clinical-btn--secondary pharmacy-compact-action" disabled={printingId === row.id} onClick={() => reprint(row)}>{printingId === row.id ? 'Ouverture…' : 'Réimprimer la facture'}</button> : '—'}</td></tr>) : <tr><td colSpan="7" className="pharmacy-empty">Aucune dispensation dans l’historique.</td></tr>}</tbody>
      </table>
    </div>
  </section>;
}
