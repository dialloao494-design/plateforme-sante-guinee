import { formatClinicalDateTime, formatClinicalStatus } from '../../../utils/clinicalPresentation.js';

export default function LabQueuePanel({ bucketTitle, bucket, loading, rows }) {
  return (
    <section className="lab-his-queue-panel" aria-live="polite">
      <h3>{bucketTitle}</h3>
      {loading ? (
        <p className="clinical-hint">Chargement…</p>
      ) : rows.length === 0 ? (
        <p className="clinical-hint">Aucun patient dans cette file.</p>
      ) : (
        <div className="lab-his-results-wrap">
          <table className="lab-his-queue-table">
            <thead>
              <tr>
                <th>N° dossier</th><th>Nom</th><th>Prénom</th><th>Examens / services demandés</th>
                {bucket === 'validated_today' && <th>Résumé des résultats</th>}
                <th>Statut</th><th>Date / heure</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={`${row.patient_id}-${row.date_time || row.exams}`}>
                  <td translate="no">{row.patient_number || row.patient_id}</td>
                  <td>{row.last_name}</td><td>{row.first_name}</td><td>{row.exams}</td>
                  {bucket === 'validated_today' && (
                    <td className="lab-his-queue-summary">
                      {row.result_summary || '—'}{row.technician ? ` · ${row.technician}` : ''}
                    </td>
                  )}
                  <td>{formatClinicalStatus(row.status)}</td>
                  <td>{formatClinicalDateTime(row.date_time)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
