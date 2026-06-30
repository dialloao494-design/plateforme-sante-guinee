import { useCallback, useEffect, useState } from 'react';

import clinicalApi from '../../services/clinicalApi';

import ClinicalStatGrid from './ClinicalStatGrid.jsx';

import './clinical.css';

const MODALITY_LABELS = { xray: 'Radiographie', ultrasound: 'Échographie', ct_scan: 'Scanner', mri: 'IRM' };

export default function RadiologyDashboard() {
  const [orders, setOrders] = useState([]);
  const [selected, setSelected] = useState(null);
  const [reportForm, setReportForm] = useState({ findings: '', impression: '', recommendations: '' });
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    try {
      const { data } = await clinicalApi.radiologyQueue();
      setOrders(data || []);
      setError('');
    } catch (err) {
      setError(err?.response?.data?.detail || 'Imagerie médicale indisponible');
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const schedule = async (orderId) => {
    try {
      await clinicalApi.updateRadiologyOrder(orderId, { status: 'scheduled' });
      setMessage('Examen planifié');
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Planification impossible');
    }
  };

  const submitReport = async () => {
    if (!selected) return;
    try {
      await clinicalApi.submitRadiologyReport(selected.id, reportForm);
      setMessage('Compte-rendu enregistré');
      setReportForm({ findings: '', impression: '', recommendations: '' });
      setSelected(null);
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'CR impossible');
    }
  };

  const validate = async (resultId) => {
    try {
      await clinicalApi.validateRadiologyResult(resultId);
      setMessage('CR validé');
      load();
    } catch (err) {
      setError(err?.response?.data?.detail || 'Validation impossible');
    }
  };

  const downloadPdf = async (resultId) => {
    try {
      await clinicalApi.downloadRadiologyPdf(resultId, `imagerie-${resultId}.pdf`);
    } catch (err) {
      setError(err?.response?.data?.detail || 'PDF indisponible');
    }
  };

  const stats = [
    { label: 'File imagerie', value: orders.length, hint: 'Actifs' },
    { label: 'Urgent', value: orders.filter((o) => o.priority === 'urgent').length, hint: 'Priorité', variant: 'warning' },
  ];

  return (
    <div className="clinical-page">
      <header className="clinical-header">
        <h1>Imagerie médicale</h1>
        <p>RX, échographie, scanner — prescription à validation médecin.</p>
      </header>
      {error && <div className="clinical-alert clinical-alert--error">{String(error)}</div>}
      {message && <div className="clinical-alert clinical-alert--success">{message}</div>}
      <ClinicalStatGrid stats={stats} />

      <div className="clinical-grid clinical-grid--2">
        <section className="clinical-panel">
          <h2>File d&apos;attente</h2>
          <ul className="clinical-queue">
            {orders.map((o) => (
              <li key={o.id}>
                <strong>{o.patient_name}</strong>
                <span className="clinical-badge">{MODALITY_LABELS[o.modality] || o.modality}</span>
                <span className="clinical-badge clinical-badge--muted">{o.status}</span>
                <div>{o.body_part || '—'} · {o.clinical_indication || ''}</div>
                <div className="clinical-actions">
                  {o.status === 'ordered' && (
                    <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => schedule(o.id)}>Planifier</button>
                  )}
                  <button type="button" className="clinical-btn" onClick={() => setSelected(o)}>Saisir CR</button>
                </div>
                {(o.results || []).map((r) => (
                  <div key={r.id} style={{ marginTop: '0.5rem' }}>
                    <small>{r.impression}</small>
                    {r.status === 'reported' && (
                      <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => validate(r.id)}>Valider</button>
                    )}
                    {r.status === 'validated' && (
                      <button type="button" className="clinical-btn clinical-btn--secondary" onClick={() => downloadPdf(r.id)}>PDF</button>
                    )}
                  </div>
                ))}
              </li>
            ))}
          </ul>
        </section>

        <section className="clinical-panel">
          <h2>Compte-rendu</h2>
          {selected ? (
            <div className="clinical-form">
              <p>{selected.patient_name} — {MODALITY_LABELS[selected.modality]}</p>
              <label>Constats<textarea rows={3} value={reportForm.findings} onChange={(e) => setReportForm({ ...reportForm, findings: e.target.value })} /></label>
              <label>Conclusion<textarea rows={2} value={reportForm.impression} onChange={(e) => setReportForm({ ...reportForm, impression: e.target.value })} /></label>
              <label>Recommandations<textarea rows={2} value={reportForm.recommendations} onChange={(e) => setReportForm({ ...reportForm, recommendations: e.target.value })} /></label>
              <button type="button" className="clinical-btn" onClick={submitReport}>Enregistrer CR</button>
            </div>
          ) : (
            <p>Sélectionnez un examen pour saisir le compte-rendu.</p>
          )}
        </section>
      </div>
    </div>
  );
}
