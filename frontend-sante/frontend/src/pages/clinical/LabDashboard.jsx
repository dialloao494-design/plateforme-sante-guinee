import { useCallback, useEffect, useState } from 'react';
import clinicalApi from '../../services/clinicalApi';
import ClinicalStatGrid from './ClinicalStatGrid.jsx';
import DepartmentQueuePanel from './DepartmentQueuePanel.jsx';
import './clinical.css';

const VALIDATED_KEY = 'clinical_lab_validated_results';

function loadValidatedHistory() {
  try {
    const raw = sessionStorage.getItem(VALIDATED_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveValidatedHistory(items) {
  sessionStorage.setItem(VALIDATED_KEY, JSON.stringify(items.slice(0, 50)));
}

export default function LabDashboard() {
  const [orders, setOrders] = useState([]);
  const [validated, setValidated] = useState(loadValidatedHistory);
  const [tab, setTab] = useState('pending');
  const [selected, setSelected] = useState(null);
  const [resultForm, setResultForm] = useState({
    result_summary: '',
    reference_range: '',
    interpretation: '',
  });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await clinicalApi.labQueue();
      setOrders(data || []);
    } catch (err) {
      setError(err?.response?.data?.detail || 'File laboratoire indisponible');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const updateStatus = async (id, status) => {
    try {
      await clinicalApi.updateLabOrder(id, { status });
      setMessage(`Commande #${id} → ${status}`);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Mise à jour impossible');
    }
  };

  const submitResult = async () => {
    if (!selected) return;
    try {
      const { data } = await clinicalApi.recordLabResult(selected.id, resultForm);
      await clinicalApi.validateLabResult(data.id);
      const entry = {
        id: data.id,
        orderId: selected.id,
        test_name: selected.test_name,
        test_code: selected.test_code,
        patient_name: selected.patient_name,
        summary: resultForm.result_summary,
        validated_at: new Date().toISOString(),
      };
      const next = [entry, ...validated.filter((v) => v.orderId !== selected.id)];
      setValidated(next);
      saveValidatedHistory(next);
      setMessage(`Résultat validé pour ${selected.test_name}`);
      setSelected(null);
      setResultForm({ result_summary: '', reference_range: '', interpretation: '' });
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Saisie résultat impossible');
    }
  };

  const downloadPdf = async (resultId, testName) => {
    try {
      await clinicalApi.downloadLabPdf(resultId, `lab-${testName || resultId}.pdf`);
    } catch (err) {
      setError(err?.response?.data?.detail || 'PDF indisponible');
    }
  };

  const stats = [
    { label: 'Examens en cours', value: orders.length, variant: 'accent' },
    { label: 'En prélèvement', value: orders.filter((o) => o.status === 'ordered').length },
    { label: 'En analyse', value: orders.filter((o) => o.status === 'in_analysis' || o.status === 'sample_collected').length, variant: 'warning' },
    { label: 'Résultats validés', value: validated.length, variant: 'success' },
  ];

  return (
    <div className="clinical-page">
      <h1>Tableau de bord — Laboratoire</h1>
      <p className="clinical-lead">Examens en attente, saisie et validation des résultats.</p>
      {error && <p className="clinical-error">{String(error)}</p>}
      {message && <p className="clinical-success">{message}</p>}

      <ClinicalStatGrid stats={stats} />

      <DepartmentQueuePanel department="lab" title="File de visite — Laboratoire" />

      <div className="clinical-tabs" role="tablist">
        <button type="button" className={`clinical-tab${tab === 'pending' ? ' active' : ''}`} onClick={() => setTab('pending')}>
          Examens en cours ({orders.length})
        </button>
        <button type="button" className={`clinical-tab${tab === 'validated' ? ' active' : ''}`} onClick={() => setTab('validated')}>
          Résultats validés ({validated.length})
        </button>
      </div>

      {tab === 'pending' && (
        <div className="clinical-grid">
          <section className="clinical-card">
            <h2>Examens en attente</h2>
            <ul className="clinical-list">
              {orders.map((order) => (
                <li key={order.id}>
                  <strong>{order.test_name}</strong> ({order.test_code})
                  <br />
                  {order.patient_name} · <span className="clinical-badge">{order.status}</span>
                  <div className="clinical-actions">
                    {order.status === 'ordered' && (
                      <button type="button" className="clinical-btn secondary" onClick={() => updateStatus(order.id, 'sample_collected')}>Prélèvement</button>
                    )}
                    {order.status === 'sample_collected' && (
                      <button type="button" className="clinical-btn secondary" onClick={() => updateStatus(order.id, 'in_analysis')}>En analyse</button>
                    )}
                    <button type="button" className="clinical-btn" onClick={() => setSelected(order)}>Saisir résultat</button>
                  </div>
                </li>
              ))}
              {orders.length === 0 && <li>Aucun examen en cours.</li>}
            </ul>
          </section>

          {selected && (
            <section className="clinical-card">
              <h2>Saisie résultat — {selected.test_name}</h2>
              <p>{selected.patient_name}</p>
              <div className="clinical-field">
                <label>Résumé</label>
                <textarea rows={3} value={resultForm.result_summary} onChange={(e) => setResultForm({ ...resultForm, result_summary: e.target.value })} required />
              </div>
              <div className="clinical-field">
                <label>Valeurs de référence</label>
                <input value={resultForm.reference_range} onChange={(e) => setResultForm({ ...resultForm, reference_range: e.target.value })} />
              </div>
              <div className="clinical-field">
                <label>Interprétation</label>
                <textarea rows={2} value={resultForm.interpretation} onChange={(e) => setResultForm({ ...resultForm, interpretation: e.target.value })} />
              </div>
              <button type="button" className="clinical-btn" onClick={submitResult}>Valider le résultat</button>
            </section>
          )}
        </div>
      )}

      {tab === 'validated' && (
        <section className="clinical-card">
          <h2>Résultats validés</h2>
          <ul className="clinical-list">
            {validated.length === 0 && <li>Aucun résultat validé en session — validez un examen pour l&apos;afficher ici.</li>}
            {validated.map((item) => (
              <li key={item.id || item.orderId}>
                <strong>{item.test_name}</strong> ({item.test_code})
                <br />
                {item.patient_name}
                <br />
                <span className="clinical-badge">validé</span>
                {' · '}
                {item.validated_at ? new Date(item.validated_at).toLocaleString('fr-FR') : ''}
                {item.summary && (
                  <>
                    <br />
                    <span className="clinical-lead">{item.summary}</span>
                  </>
                )}
                {item.id && (
                  <div className="clinical-actions">
                    <button type="button" className="clinical-btn secondary" onClick={() => downloadPdf(item.id, item.test_name)}>PDF</button>
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

