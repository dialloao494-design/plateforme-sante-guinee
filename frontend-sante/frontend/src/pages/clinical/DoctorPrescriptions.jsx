import { useCallback, useEffect, useState } from 'react';

import ClinicalFeedback from '../../components/clinical/ClinicalFeedback.jsx';
import clinicalApi from '../../services/clinicalApi.js';
import { formatApiError } from '../../utils/apiError.js';
import './DoctorPrescriptions.css';

const STATUS_LABELS = {
  active: 'À préparer',
  partially_dispensed: 'Partiellement délivrée',
  dispensed: 'Délivrée',
  cancelled: 'Annulée',
};

export default function DoctorPrescriptions() {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const { data } = await clinicalApi.doctorPrescriptions();
      setRows(data || []);
    } catch (err) {
      setError(formatApiError(err, 'Chargement des ordonnances impossible'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const normalizedQuery = query.trim().toLocaleLowerCase('fr');
  const visibleRows = normalizedQuery
    ? rows.filter((row) => [
        row.patient_name,
        row.notes,
        ...(row.items || []).flatMap((item) => [item.medication_name, item.dosage]),
      ].some((value) => String(value || '').toLocaleLowerCase('fr').includes(normalizedQuery)))
    : rows;

  return (
    <div className="clinical-page doctor-rx-page">
      <header className="doctor-rx-hero">
        <div>
          <p className="doctor-rx-eyebrow">Circuit médicament</p>
          <h1>Ordonnances</h1>
          <p>Retrouvez les traitements prescrits et leur état de délivrance à la pharmacie.</p>
        </div>
        <button type="button" className="clinical-btn secondary" onClick={load} disabled={loading}>
          {loading ? 'Actualisation…' : 'Actualiser'}
        </button>
      </header>

      <ClinicalFeedback error={error} />

      <section className="doctor-rx-toolbar" aria-label="Recherche des ordonnances">
        <label htmlFor="doctor-rx-search">Patient ou médicament</label>
        <input
          id="doctor-rx-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ex. Diallo, amoxicilline…"
          autoComplete="off"
        />
        <span aria-live="polite">{visibleRows.length} ordonnance{visibleRows.length === 1 ? '' : 's'}</span>
      </section>

      <div className="doctor-rx-list" aria-busy={loading}>
        {!loading && visibleRows.length === 0 && (
          <p className="doctor-rx-empty">Aucune ordonnance ne correspond à cette recherche.</p>
        )}
        {visibleRows.map((row) => (
          <article className="doctor-rx-card" key={row.id}>
            <header>
              <div>
                <p className="doctor-rx-number">ORD-{String(row.id).padStart(6, '0')}</p>
                <h2>{row.patient_name || 'Patient'}</h2>
                <p>{row.created_at ? new Intl.DateTimeFormat('fr-FR', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(row.created_at)) : 'Date non disponible'}</p>
              </div>
              <span className={`doctor-rx-status doctor-rx-status--${row.status}`}>
                {STATUS_LABELS[row.status] || row.status}
              </span>
            </header>
            <div className="doctor-rx-table-wrap">
              <table>
                <thead><tr><th>Médicament</th><th>Dose</th><th>Voie</th><th>Fréquence</th><th>Durée</th><th>Quantité</th></tr></thead>
                <tbody>
                  {(row.items || []).map((item, index) => (
                    <tr key={`${row.id}-${index}`}>
                      <td>{item.medication_name}</td><td>{item.dosage}</td><td>{item.route}</td>
                      <td>{item.frequency}</td><td>{item.duration_days ? `${item.duration_days} j` : '—'}</td>
                      <td>{item.quantity ?? '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {row.notes && <p className="doctor-rx-notes"><strong>Consignes :</strong> {row.notes}</p>}
          </article>
        ))}
      </div>
    </div>
  );
}
