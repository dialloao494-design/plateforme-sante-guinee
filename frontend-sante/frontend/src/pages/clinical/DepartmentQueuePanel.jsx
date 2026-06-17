import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import './clinical.css';

const WORKFLOW_LABELS = {
  child: 'Enfant',
  adult_doctor: 'Adulte → Médecin',
  adult_lab: 'Adulte → Laboratoire',
  adult_midwife: 'Adulte → Sage-femme',
};

export default function DepartmentQueuePanel({ department, title, onSelectPatient }) {
  const [queue, setQueue] = useState([]);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const { data } = await clinicalApi.workflowQueue(department);
      setQueue(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'File de visite indisponible');
    }
  }, [department]);

  useEffect(() => {
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, [load]);

  const completeStep = async (item) => {
    setLoading(true);
    setError('');
    setMessage('');
    try {
      await clinicalApi.completeWorkflowStep(item.id, department);
      setMessage(`${item.patient_name} — étape terminée, patient envoyé au service suivant`);
      if (onSelectPatient) {
        onSelectPatient(item);
      }
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Impossible de clôturer l\'étape');
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="clinical-card">
      <div className="clinical-inline-form" style={{ justifyContent: 'space-between', marginBottom: '0.75rem' }}>
        <h2>{title || 'File de visite'}</h2>
        <button type="button" className="clinical-btn secondary clinical-btn-sm" onClick={load}>
          Actualiser
        </button>
      </div>
      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}
      {queue.length === 0 ? (
        <p className="clinical-stat-hint">Aucun patient en attente dans ce service.</p>
      ) : (
        <table className="clinical-table">
          <thead>
            <tr>
              <th>Patient</th>
              <th>Âge</th>
              <th>Parcours</th>
              <th>Depuis</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {queue.map((item) => (
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
                    disabled={loading}
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
