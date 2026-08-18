import { useCallback, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import { usePollingQuery } from '../../hooks/usePollingQuery.js';
import './clinical.css';
const WORKFLOW_LABELS = {
  child: 'Enfant',
  adult_doctor: 'Adulte → Médecin',
  adult_lab: 'Adulte → Laboratoire',
  adult_midwife: 'Adulte → Sage-femme',
};

/** Queue poll every 60s; hidden tabs pause polling. */
const QUEUE_POLL_MS = 60_000;

export default function DepartmentQueuePanel({ department, title, onSelectPatient }) {
  const fetchQueue = useCallback(
    ({ forceRefresh }) => clinicalApi.workflowQueue(department, { forceRefresh }),
    [department]
  );

  const { data: queue, error, loading, refresh } = usePollingQuery(fetchQueue, {
    pollMs: QUEUE_POLL_MS,
    initialData: [],
  });

  const [message, setMessage] = useState('');
  const [actionError, setActionError] = useState('');
  const [busy, setBusy] = useState(false);

  const completeStep = async (item) => {
    setBusy(true);
    setActionError('');
    setMessage('');
    try {
      await clinicalApi.completeWorkflowStep(item.id, department);
      setMessage(`${item.patient_name} — étape terminée, patient envoyé au service suivant`);
      if (onSelectPatient) {
        onSelectPatient(item);
      }
      refresh();
    } catch (err) {
      setActionError(err?.response?.data?.detail || 'Impossible de clôturer l\'étape');
    } finally {
      setBusy(false);
    }
  };

  const rows = Array.isArray(queue) ? queue : [];

  return (
    <section className="clinical-card">
      <div className="clinical-inline-form" style={{ justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <h2>{title || 'File de visite'}</h2>
        <button type="button" className="clinical-btn secondary clinical-btn-sm" onClick={refresh}>
          Actualiser
        </button>
      </div>
      {(error || actionError) && (
        <div className="clinical-retry-bar">
          <p>{String(error || actionError)}</p>
          <button type="button" className="clinical-btn secondary clinical-btn-sm" onClick={refresh}>
            Réessayer
          </button>
        </div>
      )}
      {message && <p className="clinical-success">{message}</p>}
      {loading && rows.length === 0 ? (
        <p className="clinical-stat-hint">Chargement de la file…</p>
      ) : rows.length === 0 ? (
        <p className="clinical-stat-hint">Aucun patient en attente dans ce service.</p>
      ) : (
        <table className="clinical-table">
          <thead>
            <tr>
              <th>Patient</th>
              <th>Âge</th>
              <th>Parcours</th>
              <th>Depuis</th>
              <th scope="col">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((item) => (
              <tr key={item.id}>
                <td>
                  <strong>{item.patient_name}</strong>
                  {item.patient_phone && <div className="clinical-stat-hint">{item.patient_phone}</div>}
                </td>
                <td>{item.patient_age ?? '—'}</td>
                <td>{WORKFLOW_LABELS[item.workflow_type] || item.workflow_type}</td>
                <td>{new Date(item.started_at).toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</td>
                <td>
                  <button
                    type="button"
                    className="clinical-btn primary clinical-btn-sm"
                    disabled={busy}
                    onClick={() => completeStep(item)}
                  >
                    Terminer l&apos;étape
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
