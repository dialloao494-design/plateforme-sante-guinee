import { useCallback, useEffect, useMemo, useState } from 'react';
import clinicalApi from '../../../services/clinicalApi.js';
import { formatApiError } from '../../../utils/apiError.js';
import { formatClinicalDate, formatClinicalTime } from '../../../utils/clinicalPresentation.js';

const STATUS = { dispensed: 'Délivrée', partially_dispensed: 'Partielle', cancelled: 'Annulée' };

export default function PharmacyHistoryTab() {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState('');
  const [error, setError] = useState('');
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
  return <section className="pharmacy-panel" aria-labelledby="pharmacy-history-title">
    <div className="pharmacy-panel-header"><div><p className="pharmacy-section-kicker">Traçabilité</p><h2 id="pharmacy-history-title">Historique des dispensations</h2></div><label className="pharmacy-history-search">Rechercher<input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="N°, patient ou médicament…" /></label></div>
    {error && <p className="clinical-message clinical-message--err" role="alert">{error}</p>}
    <div className="pharmacy-table-wrap" tabIndex="0" role="region" aria-label="Historique des patients servis">
      <table className="pharmacy-table"><thead><tr><th>N° demande</th><th>Date et heure</th><th>Patient</th><th>Médicaments</th><th>Délivré par</th><th>État</th></tr></thead>
        <tbody>{filtered.length ? filtered.map((row) => <tr key={row.id}><td><strong>{row.request_number}</strong></td><td>{formatClinicalDate(row.dispensed_at || row.created_at)}<br/><small>{formatClinicalTime(row.dispensed_at || row.created_at)}</small></td><td>{row.patient_name || '—'}</td><td>{row.medications || '—'}</td><td>{row.prepared_by || '—'}</td><td><span className={`pharmacy-badge pharmacy-badge--${row.status === 'dispensed' ? 'success' : row.status === 'cancelled' ? 'muted' : 'info'}`}>{STATUS[row.status] || row.status}</span></td></tr>) : <tr><td colSpan="6" className="pharmacy-empty">Aucune dispensation dans l’historique.</td></tr>}</tbody>
      </table>
    </div>
  </section>;
}
